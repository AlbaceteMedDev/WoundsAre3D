// ARLiDARCaptureSession.swift
// AlbaceteMedDev
//
// Manages the ARKit session and performs a 5-frame LiDAR burst capture
// at 500ms intervals.

import ARKit
import UIKit
import simd

// MARK: - Captured Frame

/// All data captured from a single ARKit LiDAR frame.
struct CapturedFrame {
    let index: Int                          // 1-based frame number
    let rgbImage: UIImage                   // Best-quality color frame
    let depthData: Data                     // Raw ARDepthData as float32 array
    let confidenceData: Data                // Confidence map as uint8 array
    let intrinsics: CameraIntrinsics        // Camera intrinsic parameters
    let metadata: FrameMetadata            // Timestamp and orientation
}

struct CameraIntrinsics: Encodable {
    let fx: Float   // Focal length X
    let fy: Float   // Focal length Y
    let cx: Float   // Principal point X
    let cy: Float   // Principal point Y
    let width: Int
    let height: Int
}

struct FrameMetadata: Encodable {
    let frameIndex: Int
    let timestamp: Double
    let capturedAt: String
    let deviceOrientation: String
}

// MARK: - ARLiDARCaptureSession

@MainActor
final class ARLiDARCaptureSession: NSObject, ObservableObject {

    // MARK: Published State

    @Published private(set) var isRunning = false
    @Published private(set) var isCapturing = false
    @Published private(set) var capturedFrames: [CapturedFrame] = []
    @Published private(set) var error: Error?

    // MARK: AR Session

    let arSession = ARSession()
    private var captureTask: Task<Void, Never>?

    // MARK: - Lifecycle

    override init() {
        super.init()
        arSession.delegate = self
    }

    /// Starts the ARKit session with LiDAR depth enabled.
    func start() {
        guard ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) else {
            error = CaptureError.lidarNotSupported
            return
        }

        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = [.sceneDepth, .smoothedSceneDepth]
        config.videoFormat = preferredVideoFormat()

        arSession.run(config, options: [.resetTracking, .removeExistingAnchors])
        isRunning = true
    }

    /// Stops the ARKit session.
    func stop() {
        arSession.pause()
        isRunning = false
    }

    // MARK: - Burst Capture

    /// Captures 5 LiDAR frames at 500ms intervals.
    /// Returns the array of captured frames when complete.
    @discardableResult
    func captureBurst() async throws -> [CapturedFrame] {
        guard isRunning else { throw CaptureError.sessionNotRunning }
        guard !isCapturing else { throw CaptureError.captureAlreadyInProgress }

        isCapturing = true
        capturedFrames = []
        defer { isCapturing = false }

        var frames: [CapturedFrame] = []

        for frameIndex in 1...AppConstants.Capture.frameCount {
            // Wait for a valid frame with depth data
            let frame = try await waitForValidFrame()

            let captured = try extractFrame(from: frame, index: frameIndex)
            frames.append(captured)

            // Wait 500ms before next capture (skip delay after last frame)
            if frameIndex < AppConstants.Capture.frameCount {
                try await Task.sleep(
                    nanoseconds: UInt64(AppConstants.Capture.frameIntervalSeconds * 1_000_000_000)
                )
            }
        }

        capturedFrames = frames
        return frames
    }

    // MARK: - Private Helpers

    /// Waits up to 2 seconds for a valid ARFrame with depth data.
    private func waitForValidFrame() async throws -> ARFrame {
        let maxWaitNanoseconds: UInt64 = 2_000_000_000
        let pollInterval: UInt64 = 50_000_000 // 50ms

        var elapsed: UInt64 = 0
        while elapsed < maxWaitNanoseconds {
            if let frame = arSession.currentFrame,
               frame.sceneDepth != nil {
                return frame
            }
            try await Task.sleep(nanoseconds: pollInterval)
            elapsed += pollInterval
        }
        throw CaptureError.noDepthDataAvailable
    }

    /// Extracts all required data from an ARFrame.
    private func extractFrame(from frame: ARFrame, index: Int) throws -> CapturedFrame {
        // RGB image
        let rgbImage = UIImage(pixelBuffer: frame.capturedImage)
            ?? UIImage()

        // Depth data — sceneDepth is guaranteed at this point
        guard let sceneDepth = frame.sceneDepth else {
            throw CaptureError.noDepthDataAvailable
        }

        let depthData = extractDepthBuffer(from: sceneDepth.depthMap)
        let confidenceData = extractConfidenceBuffer(from: sceneDepth.confidenceMap)

        // Camera intrinsics
        let intrinsicMatrix = frame.camera.intrinsics
        let imageResolution = frame.camera.imageResolution
        let intrinsics = CameraIntrinsics(
            fx: intrinsicMatrix[0][0],
            fy: intrinsicMatrix[1][1],
            cx: intrinsicMatrix[2][0],
            cy: intrinsicMatrix[2][1],
            width: Int(imageResolution.width),
            height: Int(imageResolution.height)
        )

        // Metadata
        let formatter = ISO8601DateFormatter()
        let metadata = FrameMetadata(
            frameIndex: index,
            timestamp: frame.timestamp,
            capturedAt: formatter.string(from: Date()),
            deviceOrientation: deviceOrientationString()
        )

        return CapturedFrame(
            index: index,
            rgbImage: rgbImage,
            depthData: depthData,
            confidenceData: confidenceData,
            intrinsics: intrinsics,
            metadata: metadata
        )
    }

    /// Converts a CVPixelBuffer depth map to raw float32 binary Data.
    private func extractDepthBuffer(from pixelBuffer: CVPixelBuffer) -> Data {
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        guard let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            return Data()
        }
        let byteCount = CVPixelBufferGetDataSize(pixelBuffer)
        return Data(bytes: baseAddress, count: byteCount)
    }

    /// Converts a CVPixelBuffer confidence map to raw uint8 binary Data.
    private func extractConfidenceBuffer(from pixelBuffer: CVPixelBuffer?) -> Data {
        guard let pixelBuffer else { return Data() }
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        guard let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            return Data()
        }
        let byteCount = CVPixelBufferGetDataSize(pixelBuffer)
        return Data(bytes: baseAddress, count: byteCount)
    }

    /// Returns the current device orientation as a string for metadata.
    private func deviceOrientationString() -> String {
        switch UIDevice.current.orientation {
        case .portrait: return "portrait"
        case .portraitUpsideDown: return "portraitUpsideDown"
        case .landscapeLeft: return "landscapeLeft"
        case .landscapeRight: return "landscapeRight"
        default: return "unknown"
        }
    }

    /// Picks a 1080p video format to balance quality and performance.
    /// Using max resolution (4K) on Pro Max causes excessive CPU/GPU load.
    private func preferredVideoFormat() -> ARWorldTrackingConfiguration.VideoFormat {
        let formats = ARWorldTrackingConfiguration.supportedVideoFormats
        // Prefer 1920x1440 or similar — good enough for wound capture, won't lag the device
        let preferred = formats.first(where: { $0.imageResolution.width == 1920 })
        return preferred ?? formats[0]
    }
}

// MARK: - ARSessionDelegate

extension ARLiDARCaptureSession: ARSessionDelegate {
    nonisolated func session(_ session: ARSession, didFailWithError error: Error) {
        Task { @MainActor in
            self.error = error
            self.isRunning = false
        }
    }

    nonisolated func sessionWasInterrupted(_ session: ARSession) {
        Task { @MainActor in
            self.isRunning = false
        }
    }

    nonisolated func sessionInterruptionEnded(_ session: ARSession) {
        Task { @MainActor in
            self.start()
        }
    }
}

// MARK: - CaptureError

enum CaptureError: LocalizedError {
    case lidarNotSupported
    case sessionNotRunning
    case captureAlreadyInProgress
    case noDepthDataAvailable

    var errorDescription: String? {
        switch self {
        case .lidarNotSupported:
            return "This device does not support LiDAR. Please use an iPhone 12 Pro or later."
        case .sessionNotRunning:
            return "Camera session is not running."
        case .captureAlreadyInProgress:
            return "A capture is already in progress."
        case .noDepthDataAvailable:
            return "No depth data available. Ensure the camera has a clear view."
        }
    }
}

// MARK: - UIImage from CVPixelBuffer

extension UIImage {
    convenience init?(pixelBuffer: CVPixelBuffer) {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
            return nil
        }
        self.init(cgImage: cgImage)
    }
}
