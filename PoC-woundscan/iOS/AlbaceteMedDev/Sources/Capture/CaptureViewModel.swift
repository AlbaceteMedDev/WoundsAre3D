// CaptureViewModel.swift
// AlbaceteMedDev
//
// State machine for the capture screen.
// States: idle → scanning → uploading → processing → done / failed

import Combine
import Foundation
import SwiftUI

// MARK: - Capture State

enum CaptureState: Equatable {
    case idle
    case scanning(framesCaptured: Int)   // 0-5 frames captured
    case uploading(progress: Double)     // 0.0 - 1.0
    case processing                      // Waiting for pipeline to complete
    case done(scanId: String)            // Ready to show results
    case failed(String)                  // Error message

    var isActionable: Bool {
        self == .idle
    }

    var statusMessage: String {
        switch self {
        case .idle:
            return "Centre the wound in the circle and tap Scan."
        case .scanning(let count):
            return "Hold still — capturing frame \(min(count + 1, AppConstants.Capture.frameCount)) of \(AppConstants.Capture.frameCount)…"
        case .uploading(let progress):
            let pct = Int(progress * 100)
            return "Uploading… \(pct)%"
        case .processing:
            return "Processing scan…"
        case .done:
            return "Scan complete."
        case .failed(let message):
            return "Error: \(message)"
        }
    }
}

// MARK: - CaptureViewModel

@MainActor
final class CaptureViewModel: ObservableObject {

    // MARK: Published State

    @Published private(set) var captureState: CaptureState = .idle
    @Published private(set) var completedScanId: String?
    @Published private(set) var guidance = CaptureGuidance()

    /// Operator label stored with the scan (e.g. "W5 25cm matte"). Remembered between scans
    /// so a test series only needs the changed part edited.
    @Published var label: String = UserDefaults.standard.string(forKey: CaptureViewModel.labelKey) ?? "" {
        didSet { UserDefaults.standard.set(label, forKey: CaptureViewModel.labelKey) }
    }

    private static let labelKey = "scanLabel"
    private static let maxConcurrentUploads = 6

    // MARK: Dependencies

    let captureSession = ARLiDARCaptureSession()
    private let apiClient = ScanAPIClient()

    init() {
        captureSession.$guidance
            .receive(on: DispatchQueue.main)
            .assign(to: &$guidance)
    }

    /// Scan is allowed when idle and, if guidance is enforced, every live check passes.
    var canScan: Bool {
        captureState.isActionable && (!AppConstants.Guidance.enforce || guidance.isReady)
    }

    // MARK: - Public Actions

    /// Starts the ARKit session.
    func startSession() {
        captureSession.start()
    }

    /// Stops the ARKit session.
    func stopSession() {
        captureSession.stop()
    }

    /// Main scan action: capture → upload → poll until complete.
    func startScan() {
        guard canScan else { return }

        Task {
            await runScanPipeline()
        }
    }

    /// Resets to idle so the user can scan again.
    func reset() {
        captureState = .idle
        completedScanId = nil
    }

    // MARK: - Private Pipeline

    private func runScanPipeline() async {
        let trimmedLabel = label.trimmingCharacters(in: .whitespacesAndNewlines)
        let scanLabel: String? = trimmedLabel.isEmpty ? nil : trimmedLabel
        let guidanceAtPress = guidance

        do {
            // Step 1 — One burst of 5 LiDAR frames
            captureState = .scanning(framesCaptured: 0)
            let frames = try await captureSession.captureBurst(label: scanLabel) { [weak self] count in
                self?.captureState = .scanning(framesCaptured: count)
            }

            // Step 2 — Create scan on backend, get presigned URLs
            captureState = .uploading(progress: 0.0)
            let sessionPayload = buildSessionPayload(label: scanLabel, guidance: guidanceAtPress)
            let scanResponse = try await apiClient.createScan(sessionPayload: sessionPayload)

            // Step 3 — Upload all 25 files via presigned PUT URLs
            try await uploadFrames(frames, uploadUrls: scanResponse.uploadUrls)

            // Step 4 — Poll status until COMPLETE or FAILED
            captureState = .processing
            try await pollUntilComplete(scanId: scanResponse.scanId)

            // Step 5 — Done
            completedScanId = scanResponse.scanId
            captureState = .done(scanId: scanResponse.scanId)

        } catch {
            captureState = .failed(error.localizedDescription)
        }
    }

    // MARK: - Upload

    private struct UploadJob: Sendable {
        let filename: String
        let data: Data
        let contentType: String
        let url: URL
    }

    /// Uploads every file, a few at a time, updating progress as each one finishes.
    private func uploadFrames(_ frames: [CapturedFrame], uploadUrls: [String: String]) async throws {
        var jobs: [UploadJob] = []
        for frame in frames {
            for (filename, data, contentType) in try buildUploadFiles(for: frame) {
                guard let urlString = uploadUrls[filename], let url = URL(string: urlString) else {
                    throw ScanAPIError.uploadFailed(filename)
                }
                jobs.append(UploadJob(filename: filename, data: data, contentType: contentType, url: url))
            }
        }

        let client = apiClient
        let total = jobs.count
        var finished = 0
        var pending = jobs.makeIterator()

        try await withThrowingTaskGroup(of: Void.self) { group in
            for _ in 0..<min(Self.maxConcurrentUploads, total) {
                if let job = pending.next() {
                    group.addTask { try await client.uploadFile(data: job.data, to: job.url, contentType: job.contentType) }
                }
            }
            while try await group.next() != nil {
                finished += 1
                captureState = .uploading(progress: Double(finished) / Double(total))
                if let job = pending.next() {
                    group.addTask { try await client.uploadFile(data: job.data, to: job.url, contentType: job.contentType) }
                }
            }
        }
    }

    /// Builds the (filename, data, contentType) tuples for a single frame.
    private func buildUploadFiles(for frame: CapturedFrame) throws -> [(String, Data, String)] {
        var files: [(String, Data, String)] = []
        let i = frame.index

        // RGB JPEG
        guard let jpegData = frame.rgbImage.jpegData(compressionQuality: 0.92) else {
            throw CaptureError.imageConversionFailed
        }
        files.append(("frame_\(i)_rgb.jpg", jpegData, "image/jpeg"))

        // Depth binary
        files.append(("frame_\(i)_depth.bin", frame.depthData, "application/octet-stream"))

        // Confidence binary
        files.append(("frame_\(i)_confidence.bin", frame.confidenceData, "application/octet-stream"))

        // Intrinsics JSON
        let intrinsicsData = try JSONEncoder().encode(frame.intrinsics)
        files.append(("frame_\(i)_intrinsics.json", intrinsicsData, "application/json"))

        // Metadata JSON
        let metadataData = try JSONEncoder().encode(frame.metadata)
        files.append(("frame_\(i)_metadata.json", metadataData, "application/json"))

        return files
    }

    // MARK: - Polling

    private func pollUntilComplete(scanId: String) async throws {
        for attempt in 0..<AppConstants.Polling.maxAttempts {
            let statusResponse = try await apiClient.getScanStatus(scanId: scanId)

            switch statusResponse.status {
            case .complete:
                return
            case .failed:
                throw PipelineError.processingFailed
            case .uploading, .processing:
                // Still running — wait and retry
                if attempt < AppConstants.Polling.maxAttempts - 1 {
                    try await Task.sleep(
                        nanoseconds: UInt64(AppConstants.Polling.intervalSeconds * 1_000_000_000)
                    )
                }
            }
        }
        throw PipelineError.timeout
    }

    // MARK: - Session Payload

    /// Stored as-is in DynamoDB by POST /scans, so only strings, integers and booleans
    /// (DynamoDB rejects JSON floats there). Full numeric detail is in each frame's metadata.json.
    private func buildSessionPayload(label: String?, guidance: CaptureGuidance) -> [String: Any] {
        let formatter = ISO8601DateFormatter()
        var payload: [String: Any] = [
            "capturedAt": formatter.string(from: Date()),
            "frameCount": AppConstants.Capture.frameCount,
            "frameIntervalMs": Int(AppConstants.Capture.frameIntervalSeconds * 1000),
            "appVersion": DeviceInfo.appVersion,
            "deviceModel": DeviceInfo.model,
            "systemVersion": DeviceInfo.systemVersion,
            "guidanceEnforced": AppConstants.Guidance.enforce,
            "captureGuidance": guidance.summary
        ]
        if let label {
            payload["label"] = label
        }
        return payload
    }
}

// MARK: - Pipeline Errors

enum PipelineError: LocalizedError {
    case processingFailed
    case timeout

    var errorDescription: String? {
        switch self {
        case .processingFailed:
            return "Scan processing failed on the server."
        case .timeout:
            return "Processing is taking longer than expected. Please try again."
        }
    }
}
