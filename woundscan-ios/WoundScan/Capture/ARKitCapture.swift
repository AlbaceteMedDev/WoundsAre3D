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

    let session = ARSession()
    private var burstActive = false
    private var burstFrames: [CapturedFrame] = []
    private var startTimestamp: TimeInterval = 0
    private var continuation: CheckedContinuation<[CapturedFrame], Error>?

    struct CapturedFrame {
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
        Task { @MainActor in
            guard burstActive, let depth = frame.sceneDepth ?? frame.smoothedSceneDepth else {
                self.motionScore = self.computeMotionScore(camera: frame.camera)
                return
            }
            burstFrames.append(
                CapturedFrame(
                    timestamp: frame.timestamp,
                    depth: depth,
                    pixelBuffer: frame.capturedImage,
                    camera: frame.camera
                )
            )
            frameCount = burstFrames.count
            motionScore = computeMotionScore(camera: frame.camera)
            if burstFrames.count >= frameLimit {
                let collected = burstFrames
                burstFrames.removeAll()
                burstActive = false
                continuation?.resume(returning: collected)
                continuation = nil
            }
        }
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
