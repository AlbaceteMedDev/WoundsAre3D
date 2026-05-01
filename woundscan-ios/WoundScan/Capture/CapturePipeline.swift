import ARKit
import Foundation

/// High-level orchestration of the iOS capture flow.
///
/// Steps:
/// 1. Start ARKit session and wait for stable tracking
/// 2. Detect fiducials in the live feed
/// 3. Trigger 60-frame burst capture on user tap
/// 4. Extract per-frame depth, RGB, pose, intrinsics
/// 5. Persist locally for review and queued upload
@MainActor
final class CapturePipeline: ObservableObject {
    @Published var stage: Stage = .idle
    @Published var fiducialOk: Bool = false
    @Published var motionScore: Float = 1.0
    @Published var capturedArtifacts: CaptureArtifacts?

    enum Stage: Equatable {
        case idle
        case warmingUp
        case ready
        case capturing(progress: Double)
        case processing
        case done
        case failed(String)
    }

    let arkit = ARKitCapture()

    func start() async {
        stage = .warmingUp
        arkit.start()
        // Wait briefly for ARKit to stabilize
        try? await Task.sleep(nanoseconds: 500_000_000)
        stage = .ready
    }

    func captureBurst() async {
        stage = .capturing(progress: 0)
        do {
            let frames = try await arkit.captureBurst(frameLimit: 60)
            stage = .processing
            let artifacts = await processFrames(frames)
            capturedArtifacts = artifacts
            stage = .done
        } catch {
            stage = .failed(String(describing: error))
        }
    }

    private func processFrames(_ frames: [ARKitCapture.CapturedFrame]) async -> CaptureArtifacts {
        // Extract depth maps as Float arrays in cm + confidence buffers
        let depths: [Data] = frames.compactMap { f in
            depthBufferToData(f.depth.depthMap)
        }
        let confidences: [Data] = frames.compactMap { f in
            f.depth.confidenceMap.flatMap { confidenceBufferToData($0) }
        }
        let intrinsics = frames.first.map { f in
            CameraIntrinsicsRecord(
                fx: Double(f.camera.intrinsics[0, 0]),
                fy: Double(f.camera.intrinsics[1, 1]),
                cx: Double(f.camera.intrinsics[2, 0]),
                cy: Double(f.camera.intrinsics[2, 1]),
                width: Int(f.camera.imageResolution.width),
                height: Int(f.camera.imageResolution.height)
            )
        } ?? CameraIntrinsicsRecord(fx: 0, fy: 0, cx: 0, cy: 0, width: 0, height: 0)

        let poses = frames.map { f in
            let m = f.camera.transform
            let pos = m.columns.3
            // Quaternion from rotation portion of the matrix
            let r = simd_quatf(simd_float3x3(m.columns.0.xyz, m.columns.1.xyz, m.columns.2.xyz))
            return CameraPoseRecord(
                positionM: [Double(pos.x), Double(pos.y), Double(pos.z)],
                rotationQuat: [Double(r.imag.x), Double(r.imag.y), Double(r.imag.z), Double(r.real)],
                timestampS: f.timestamp
            )
        }

        return CaptureArtifacts(
            intrinsics: intrinsics,
            depthBlobs: depths,
            confidenceBlobs: confidences,
            poses: poses
        )
    }

    private func depthBufferToData(_ buffer: CVPixelBuffer) -> Data? {
        CVPixelBufferLockBaseAddress(buffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
        guard let ptr = CVPixelBufferGetBaseAddress(buffer) else { return nil }
        let bpr = CVPixelBufferGetBytesPerRow(buffer)
        let h = CVPixelBufferGetHeight(buffer)
        return Data(bytes: ptr, count: bpr * h)
    }

    private func confidenceBufferToData(_ buffer: CVPixelBuffer) -> Data? {
        CVPixelBufferLockBaseAddress(buffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
        guard let ptr = CVPixelBufferGetBaseAddress(buffer) else { return nil }
        let bpr = CVPixelBufferGetBytesPerRow(buffer)
        let h = CVPixelBufferGetHeight(buffer)
        return Data(bytes: ptr, count: bpr * h)
    }
}

struct CaptureArtifacts {
    let intrinsics: CameraIntrinsicsRecord
    let depthBlobs: [Data]
    let confidenceBlobs: [Data]
    let poses: [CameraPoseRecord]
}

private extension simd_float4 {
    var xyz: simd_float3 { simd_float3(x, y, z) }
}
