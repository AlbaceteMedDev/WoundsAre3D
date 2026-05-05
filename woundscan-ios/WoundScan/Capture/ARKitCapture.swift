import ARKit
import AVFoundation
import Combine
import CoreImage
import simd

/// ARKit-driven capture pipeline.
///
/// Configures an ARWorldTrackingConfiguration with sceneDepth + RGB,
/// captures a 60-frame burst at native resolution, and emits the buffers
/// + per-frame poses to subscribers.
@MainActor
final class ARKitCapture: NSObject, ObservableObject, ARSessionDelegate {
    @Published var isReady: Bool = false
    @Published var frameCount: Int = 0
    @Published var motionScore: Float = 1.0  // 1 = stable, 0 = moving fast
    @Published var fiducialDetected: Bool = false
    /// Distance to the centre of the depth map, in millimetres. `nil` if no depth yet.
    @Published var distanceMm: Float? = nil
    /// Pitch in degrees from horizontal. 0 = phone parallel to ground.
    @Published var pitchDeg: Float = 0
    /// Tracking quality from ARKit. .normal = green, others = warn.
    @Published var trackingState: ARCamera.TrackingState = .notAvailable

    let session = ARSession()
    private var burstActive = false
    private var burstFrames: [CapturedFrame] = []
    private var startTimestamp: TimeInterval = 0
    private var continuation: CheckedContinuation<[CapturedFrame], Error>?

    struct CapturedFrame: @unchecked Sendable {
        let timestamp: TimeInterval
        let depth: ARDepthData
        let pixelBuffer: CVPixelBuffer
        let camera: ARCamera
    }

    func start() {
        guard ARWorldTrackingConfiguration.supportsFrameSemantics([.sceneDepth, .smoothedSceneDepth]) else {
            isReady = false
            return
        }
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics.insert(.sceneDepth)
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.smoothedSceneDepth) {
            config.frameSemantics.insert(.smoothedSceneDepth)
        }
        if let videoFormat = ARWorldTrackingConfiguration.supportedVideoFormats
            .filter({ $0.imageResolution.width >= 1920 })
            .first {
            config.videoFormat = videoFormat
        }
        session.delegate = self
        session.run(config, options: [.resetTracking, .removeExistingAnchors])
        isReady = true
    }

    func pause() {
        session.pause()
        isReady = false
    }

    /// Begin a 60-frame burst. Returns when complete.
    func captureBurst(frameLimit: Int = 60) async throws -> [CapturedFrame] {
        guard !burstActive else { throw NSError(domain: "ARKitCapture", code: 1) }
        burstActive = true
        burstFrames.removeAll()
        startTimestamp = Date().timeIntervalSince1970
        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            self.burstFrames.reserveCapacity(frameLimit)
            self.frameLimit = frameLimit
        }
    }

    private var frameLimit: Int = 60

    nonisolated func session(_ session: ARSession, didUpdate frame: ARFrame) {
        let depthOpt = frame.sceneDepth ?? frame.smoothedSceneDepth
        let camera = frame.capturedImage
        let timestamp = frame.timestamp
        let arCamera = frame.camera
        let track = frame.camera.trackingState
        let centerDepth = depthOpt.flatMap { centerDepthMm(of: $0.depthMap) }
        let pitch = pitchDegrees(from: arCamera.transform)

        Task { @MainActor in
            self.trackingState = track
            self.motionScore = self.computeMotionScore(camera: arCamera)
            self.pitchDeg = pitch
            if let d = centerDepth { self.distanceMm = d }

            guard self.burstActive, let depth = depthOpt else { return }
            self.burstFrames.append(
                CapturedFrame(
                    timestamp: timestamp,
                    depth: depth,
                    pixelBuffer: camera,
                    camera: arCamera
                )
            )
            self.frameCount = self.burstFrames.count
            if self.burstFrames.count >= self.frameLimit {
                let collected = self.burstFrames
                self.burstFrames.removeAll()
                self.burstActive = false
                self.continuation?.resume(returning: collected)
                self.continuation = nil
            }
        }
    }

    private nonisolated func centerDepthMm(of buffer: CVPixelBuffer) -> Float? {
        CVPixelBufferLockBaseAddress(buffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(buffer) else { return nil }
        let w = CVPixelBufferGetWidth(buffer)
        let h = CVPixelBufferGetHeight(buffer)
        let bpr = CVPixelBufferGetBytesPerRow(buffer)
        let cx = w / 2
        let cy = h / 2
        // ARKit sceneDepth is Float32 metres.
        let row = base.advanced(by: cy * bpr)
        let pixel = row.assumingMemoryBound(to: Float.self).advanced(by: cx)
        let metres = pixel.pointee
        guard metres.isFinite, metres > 0 else { return nil }
        return metres * 1000.0
    }

    private nonisolated func pitchDegrees(from transform: simd_float4x4) -> Float {
        // Phone forward axis in world space; angle below horizontal.
        let forward = simd_normalize(simd_float3(-transform.columns.2.x,
                                                 -transform.columns.2.y,
                                                 -transform.columns.2.z))
        // pitch positive = pointing down at the wound on a table.
        let pitch = asinf(-forward.y)
        return pitch * 180.0 / .pi
    }

    private var lastTransform: simd_float4x4?
    private var lastTimestamp: TimeInterval?

    private func computeMotionScore(camera: ARCamera) -> Float {
        let now = Date().timeIntervalSince1970
        defer { lastTransform = camera.transform; lastTimestamp = now }
        guard let last = lastTransform, let lastTS = lastTimestamp else { return 1.0 }
        let dt = max(now - lastTS, 0.001)
        let dx = camera.transform.columns.3 - last.columns.3
        let speedMmPerS = simd_length(simd_float3(dx.x, dx.y, dx.z)) * 1000.0 / Float(dt)
        // Map 0-50 mm/s -> 1..0
        let s = max(0.0, min(1.0, 1.0 - speedMmPerS / 50.0))
        return s
    }
}
