// CaptureViewModel.swift
// AlbaceteMedDev
//
// State machine for the capture screen.
// States: idle → scanning → uploading → processing → done / failed

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
            return "Position the camera over the wound and tap Scan."
        case .scanning(let count):
            return "Capturing frame \(count + 1) of \(AppConstants.Capture.frameCount)…"
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

    // MARK: Dependencies

    let captureSession = ARLiDARCaptureSession()
    private let apiClient = ScanAPIClient()

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
        guard captureState.isActionable else { return }

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
        do {
            // Step 1 — Burst capture 5 LiDAR frames
            captureState = .scanning(framesCaptured: 0)
            let frames = try await captureFrames()

            // Step 2 — Create scan on backend, get presigned URLs
            captureState = .uploading(progress: 0.0)
            let sessionPayload = buildSessionPayload()
            let scanResponse = try await apiClient.createScan(sessionPayload: sessionPayload)

            // Step 3 — Upload all 25 files via presigned PUT URLs
            try await uploadFrames(frames, uploadUrls: scanResponse.uploadUrls, scanId: scanResponse.scanId)

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

    // MARK: - Capture

    private func captureFrames() async throws -> [CapturedFrame] {
        var frames: [CapturedFrame] = []

        // Capture frames one at a time, updating state for each
        for frameIndex in 1...AppConstants.Capture.frameCount {
            captureState = .scanning(framesCaptured: frameIndex - 1)

            // Wait for the next valid LiDAR frame from the session
            let frame = try await waitForValidFrame(index: frameIndex)
            frames.append(frame)

            if frameIndex < AppConstants.Capture.frameCount {
                try await Task.sleep(
                    nanoseconds: UInt64(AppConstants.Capture.frameIntervalSeconds * 1_000_000_000)
                )
            }
        }

        captureState = .scanning(framesCaptured: AppConstants.Capture.frameCount)
        return frames
    }

    private func waitForValidFrame(index: Int) async throws -> CapturedFrame {
        // Delegate to the ARKit session for the actual frame grab
        let burst = try await captureSession.captureBurst()
        guard let frame = burst.first else {
            throw CaptureError.noDepthDataAvailable
        }
        // Return a re-indexed frame
        return CapturedFrame(
            index: index,
            rgbImage: frame.rgbImage,
            depthData: frame.depthData,
            confidenceData: frame.confidenceData,
            intrinsics: frame.intrinsics,
            metadata: frame.metadata
        )
    }

    // MARK: - Upload

    private func uploadFrames(
        _ frames: [CapturedFrame],
        uploadUrls: [String: String],
        scanId: String
    ) async throws {
        let totalFiles = AppConstants.Capture.totalFileCount
        var uploadedCount = 0

        for frame in frames {
            let files = try buildUploadFiles(for: frame)

            for (filename, data, contentType) in files {
                guard let urlString = uploadUrls[filename],
                      let url = URL(string: urlString) else {
                    throw ScanAPIError.uploadFailed(filename)
                }

                try await apiClient.uploadFile(data: data, to: url, contentType: contentType)
                uploadedCount += 1

                let progress = Double(uploadedCount) / Double(totalFiles)
                captureState = .uploading(progress: progress)
            }
        }
    }

    /// Builds the (filename, data, contentType) tuples for a single frame.
    private func buildUploadFiles(for frame: CapturedFrame) throws -> [(String, Data, String)] {
        var files: [(String, Data, String)] = []
        let i = frame.index

        // RGB JPEG
        if let jpegData = frame.rgbImage.jpegData(compressionQuality: 0.92) {
            files.append(("frame_\(i)_rgb.jpg", jpegData, "image/jpeg"))
        }

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

    private func buildSessionPayload() -> [String: Any] {
        let formatter = ISO8601DateFormatter()
        return [
            "capturedAt": formatter.string(from: Date()),
            "frameCount": AppConstants.Capture.frameCount,
            "frameIntervalMs": Int(AppConstants.Capture.frameIntervalSeconds * 1000),
            "appVersion": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        ]
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
