// ARLiDARCaptureSession.swift
// AlbaceteMedDev
//
// Manages the ARKit session, publishes live capture guidance (distance, tilt,
// steadiness, tracking, light) and performs a 5-frame LiDAR burst capture at
// 500 ms intervals.

import ARKit
import UIKit
import simd

// MARK: - Captured Frame

/// All data captured from a single ARKit LiDAR frame.
struct CapturedFrame {
    let index: Int                          // 1-based frame number
    let rgbImage: UIImage                   // Best-quality color frame
    let depthData: Data                     // Depth map as packed float32 (metres)
    let confidenceData: Data                // Confidence map as packed uint8 (0 low, 1 medium, 2 high)
    let intrinsics: CameraIntrinsics        // Camera intrinsic parameters
    let metadata: FrameMetadata             // Timestamp, orientation, capture conditions
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

    // Capture conditions (added for QA; the backend ignores unknown keys).
    let label: String?                      // Operator label, e.g. "W5 25cm matte"
    let deviceModel: String                 // e.g. "iPhone16,2"
    let systemVersion: String
    let appVersion: String
    let depthSource: String                 // "smoothedSceneDepth" or "sceneDepth"
    let depthWidth: Int
    let depthHeight: Int
    let centreDistanceM: Float?             // Median LiDAR depth in the central patch
    let centreHighConfidenceFraction: Float?
    let tiltDegrees: Float?                 // 0 = camera pointing straight down
    let speedMetersPerSecond: Float?
    let angularSpeedDegreesPerSecond: Float?
    let trackingState: String
    let ambientIntensity: Float?
    let exposureDurationS: Double
    let cameraTransform: [Float]            // 4x4 world-from-camera, column-major
    let guidanceIssues: [String]            // Empty when every live check passed
}

// MARK: - Device info

@MainActor
enum DeviceInfo {
    static let model: String = {
        var info = utsname()
        uname(&info)
        return withUnsafeBytes(of: &info.machine) { raw in
            String(decoding: raw.prefix(while: { $0 != 0 }), as: UTF8.self)
        }
    }()

    static var systemVersion: String { UIDevice.current.systemVersion }

    static var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }
}

// MARK: - Capture Guidance

/// Live assessment of whether the current camera view is good to scan.
struct CaptureGuidance: Equatable {
    var distanceM: Float?
    var centreHighConfidence: Float?
    var tiltDegrees: Float?
    var speed: Float?
    var angularSpeed: Float?
    var trackingNormal = false
    var isSteady = false
    var ambientIntensity: Float?

    enum Issue: String {
        case noDepth, tracking, tooClose, tooFar, tilted, moving, lowLight
    }

    var issues: [Issue] {
        typealias G = AppConstants.Guidance
        guard let d = distanceM else { return [.noDepth] }
        var out: [Issue] = []
        if !trackingNormal { out.append(.tracking) }
        if d < G.minDistanceM { out.append(.tooClose) } else if d > G.maxDistanceM { out.append(.tooFar) }
        if let t = tiltDegrees, t > G.maxTiltDegrees { out.append(.tilted) }
        if !isSteady { out.append(.moving) }
        if let a = ambientIntensity, a < G.minAmbientIntensity { out.append(.lowLight) }
        return out
    }

    var isReady: Bool { issues.isEmpty }

    /// One short instruction for the most important issue.
    var message: String {
        typealias G = AppConstants.Guidance
        let range = "\(Int(G.minDistanceM * 100))–\(Int(G.maxDistanceM * 100)) cm"
        switch issues.first {
        case .none: return "Ready — tap Scan"
        case .noDepth: return "Point the camera at the wound"
        case .tracking: return "Move the phone slowly to start tracking"
        case .tooClose: return "Move further away (aim for \(range))"
        case .tooFar: return "Move closer (aim for \(range))"
        case .tilted: return "Hold the phone flat over the wound"
        case .moving: return "Hold still"
        case .lowLight: return "More light needed — avoid direct glare"
        }
    }

    /// String-only summary for the session payload (POST /scans stores it in DynamoDB,
    /// which rejects floating-point numbers from JSON).
    var summary: [String: String] {
        var s: [String: String] = ["issues": issues.map(\.rawValue).joined(separator: ",")]
        if let d = distanceM { s["distanceCm"] = String(format: "%.1f", d * 100) }
        if let t = tiltDegrees { s["tiltDeg"] = String(format: "%.1f", t) }
        if let c = centreHighConfidence { s["centreHighConfidence"] = String(format: "%.2f", c) }
        if let a = ambientIntensity { s["ambientIntensity"] = String(format: "%.0f", a) }
        return s
    }

    /// Measures guidance from one AR frame. `viewDirection` is the camera's forward axis in world space.
    static func measure(frame: ARFrame, viewDirection: simd_float3, speed: Float?, angularSpeed: Float?) -> CaptureGuidance {
        typealias G = AppConstants.Guidance
        var g = CaptureGuidance()
        if let depth = frame.smoothedSceneDepth ?? frame.sceneDepth {
            let stats = centreStats(depth: depth.depthMap, confidence: depth.confidenceMap)
            g.distanceM = stats.distance
            g.centreHighConfidence = stats.highConfidence
        }
        // World Y is up (gravity-aligned session), so straight down is (0, -1, 0).
        let c = max(-1, min(1, -viewDirection.y))
        g.tiltDegrees = acos(c) * 180 / .pi
        if case .normal = frame.camera.trackingState { g.trackingNormal = true }
        g.speed = speed
        g.angularSpeed = angularSpeed
        if let v = speed, let w = angularSpeed {
            g.isSteady = v <= G.maxSpeedMetersPerSecond && w <= G.maxAngularSpeedDegreesPerSecond
        }
        if let light = frame.lightEstimate { g.ambientIntensity = Float(light.ambientIntensity) }
        return g
    }

    /// Median depth and high-confidence fraction in the central 1/8 x 1/8 of the depth map.
    private static func centreStats(depth: CVPixelBuffer, confidence: CVPixelBuffer?) -> (distance: Float?, highConfidence: Float?) {
        CVPixelBufferLockBaseAddress(depth, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(depth, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(depth) else { return (nil, nil) }
        let w = CVPixelBufferGetWidth(depth), h = CVPixelBufferGetHeight(depth)
        let bpr = CVPixelBufferGetBytesPerRow(depth)
        let hx = max(2, w / 16), hy = max(2, h / 16)
        let x0 = w / 2 - hx, x1 = w / 2 + hx, y0 = h / 2 - hy, y1 = h / 2 + hy

        var values: [Float] = []
        values.reserveCapacity((x1 - x0) * (y1 - y0))
        for y in y0..<y1 {
            let row = base.advanced(by: y * bpr).assumingMemoryBound(to: Float32.self)
            for x in x0..<x1 where row[x].isFinite && row[x] > 0 {
                values.append(row[x])
            }
        }
        let distance: Float? = values.count >= 8 ? values.sorted()[values.count / 2] : nil

        var high: Float?
        if let confidence {
            CVPixelBufferLockBaseAddress(confidence, .readOnly)
            defer { CVPixelBufferUnlockBaseAddress(confidence, .readOnly) }
            if let cbase = CVPixelBufferGetBaseAddress(confidence) {
                let cbpr = CVPixelBufferGetBytesPerRow(confidence)
                var n = 0, total = 0
                for y in y0..<y1 {
                    let row = cbase.advanced(by: y * cbpr).assumingMemoryBound(to: UInt8.self)
                    for x in x0..<x1 {
                        total += 1
                        if row[x] == UInt8(ARConfidenceLevel.high.rawValue) { n += 1 }
                    }
                }
                high = total > 0 ? Float(n) / Float(total) : nil
            }
        }
        return (distance, high)
    }
}

/// Tracks camera motion between frames and rate-limits guidance updates.
/// Called from the ARSession delegate (main queue) and from the capture burst.
final class GuidanceEstimator: @unchecked Sendable {
    private let lock = NSLock()
    private var lastEmit: TimeInterval = 0
    private var lastPose: (t: TimeInterval, position: simd_float3, direction: simd_float3)?
    private var speed: Float?
    private var angularSpeed: Float?

    /// Returns new guidance when an update is due (or `force` is set), otherwise nil.
    func update(with frame: ARFrame, force: Bool = false) -> CaptureGuidance? {
        lock.lock()
        defer { lock.unlock() }

        let t = frame.timestamp
        let transform = frame.camera.transform
        let position = simd_make_float3(transform.columns.3)
        // The camera looks along its -Z axis.
        let direction = -simd_normalize(simd_make_float3(transform.columns.2))

        if let last = lastPose {
            let dt = Float(t - last.t)
            if dt >= 0.1 {
                speed = simd_distance(position, last.position) / dt
                let c = max(-1, min(1, simd_dot(direction, last.direction)))
                angularSpeed = acos(c) * 180 / .pi / dt
                lastPose = (t, position, direction)
            } else if dt < 0 {
                lastPose = (t, position, direction)       // session reset
            }
        } else {
            lastPose = (t, position, direction)
        }

        guard force || t - lastEmit >= 1.0 / AppConstants.Guidance.updateHz else { return nil }
        lastEmit = t
        return CaptureGuidance.measure(frame: frame, viewDirection: direction, speed: speed, angularSpeed: angularSpeed)
    }
}

// MARK: - ARLiDARCaptureSession

@MainActor
final class ARLiDARCaptureSession: NSObject, ObservableObject {

    // MARK: Published State

    @Published private(set) var isRunning = false
    @Published private(set) var isCapturing = false
    @Published private(set) var capturedFrames: [CapturedFrame] = []
    @Published private(set) var guidance = CaptureGuidance()
    @Published private(set) var error: Error?

    // MARK: AR Session

    let arSession = ARSession()
    nonisolated let estimator = GuidanceEstimator()

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
        config.isLightEstimationEnabled = true

        UIDevice.current.beginGeneratingDeviceOrientationNotifications()
        arSession.run(config, options: [.resetTracking, .removeExistingAnchors])
        isRunning = true
    }

    /// Stops the ARKit session.
    func stop() {
        arSession.pause()
        UIDevice.current.endGeneratingDeviceOrientationNotifications()
        isRunning = false
    }

    // MARK: - Burst Capture

    /// Captures `AppConstants.Capture.frameCount` distinct LiDAR frames at
    /// `frameIntervalSeconds` intervals. `progress` is called after each frame.
    @discardableResult
    func captureBurst(label: String? = nil, progress: (@MainActor (Int) -> Void)? = nil) async throws -> [CapturedFrame] {
        guard isRunning else { throw CaptureError.sessionNotRunning }
        guard !isCapturing else { throw CaptureError.captureAlreadyInProgress }

        isCapturing = true
        capturedFrames = []
        defer { isCapturing = false }

        var frames: [CapturedFrame] = []
        var lastTimestamp: TimeInterval = 0

        for frameIndex in 1...AppConstants.Capture.frameCount {
            let frame = try await waitForValidFrame(after: lastTimestamp)
            lastTimestamp = frame.timestamp
            let g = estimator.update(with: frame, force: true) ?? guidance

            frames.append(try extractFrame(from: frame, index: frameIndex, guidance: g, label: label))
            progress?(frameIndex)

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

    /// Waits up to 2 seconds for a new ARFrame (newer than `after`) with depth data.
    private func waitForValidFrame(after: TimeInterval) async throws -> ARFrame {
        let maxWaitNanoseconds: UInt64 = 2_000_000_000
        let pollInterval: UInt64 = 20_000_000 // 20ms

        var elapsed: UInt64 = 0
        while elapsed < maxWaitNanoseconds {
            if let frame = arSession.currentFrame,
               frame.timestamp > after,
               frame.smoothedSceneDepth != nil || frame.sceneDepth != nil {
                return frame
            }
            try await Task.sleep(nanoseconds: pollInterval)
            elapsed += pollInterval
        }
        throw CaptureError.noDepthDataAvailable
    }

    /// Extracts all required data from an ARFrame.
    private func extractFrame(from frame: ARFrame, index: Int, guidance g: CaptureGuidance, label: String?) throws -> CapturedFrame {
        guard let rgbImage = UIImage(pixelBuffer: frame.capturedImage) else {
            throw CaptureError.imageConversionFailed
        }

        // Prefer the temporally smoothed depth (less noise); fall back to the raw map.
        let depthSource: String
        let depth: ARDepthData
        if let smoothed = frame.smoothedSceneDepth {
            depth = smoothed
            depthSource = "smoothedSceneDepth"
        } else if let raw = frame.sceneDepth {
            depth = raw
            depthSource = "sceneDepth"
        } else {
            throw CaptureError.noDepthDataAvailable
        }

        let depthData = packedBytes(depth.depthMap, bytesPerPixel: MemoryLayout<Float32>.size)
        let confidenceData = depth.confidenceMap.map { packedBytes($0, bytesPerPixel: 1) } ?? Data()

        // Camera intrinsics (for the RGB image resolution)
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

        let t = frame.camera.transform
        let transform: [Float] = [t.columns.0, t.columns.1, t.columns.2, t.columns.3]
            .flatMap { [$0.x, $0.y, $0.z, $0.w] }

        let metadata = FrameMetadata(
            frameIndex: index,
            timestamp: frame.timestamp,
            capturedAt: ISO8601DateFormatter().string(from: Date()),
            deviceOrientation: deviceOrientationString(),
            label: label,
            deviceModel: DeviceInfo.model,
            systemVersion: DeviceInfo.systemVersion,
            appVersion: DeviceInfo.appVersion,
            depthSource: depthSource,
            depthWidth: CVPixelBufferGetWidth(depth.depthMap),
            depthHeight: CVPixelBufferGetHeight(depth.depthMap),
            centreDistanceM: g.distanceM,
            centreHighConfidenceFraction: g.centreHighConfidence,
            tiltDegrees: g.tiltDegrees,
            speedMetersPerSecond: g.speed,
            angularSpeedDegreesPerSecond: g.angularSpeed,
            trackingState: trackingStateString(frame.camera.trackingState),
            ambientIntensity: g.ambientIntensity,
            exposureDurationS: frame.camera.exposureDuration,
            cameraTransform: transform,
            guidanceIssues: g.issues.map(\.rawValue)
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

    /// Copies a pixel buffer row by row, dropping any row padding, so the backend can
    /// read it as a plain width x height array.
    private func packedBytes(_ pixelBuffer: CVPixelBuffer, bytesPerPixel: Int) -> Data {
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        guard let base = CVPixelBufferGetBaseAddress(pixelBuffer) else { return Data() }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        let rowBytes = width * bytesPerPixel

        if bytesPerRow == rowBytes {
            return Data(bytes: base, count: rowBytes * height)
        }
        var data = Data(capacity: rowBytes * height)
        for y in 0..<height {
            data.append(base.advanced(by: y * bytesPerRow).assumingMemoryBound(to: UInt8.self), count: rowBytes)
        }
        return data
    }

    /// Returns the current device orientation as a string for metadata.
    private func deviceOrientationString() -> String {
        switch UIDevice.current.orientation {
        case .portrait: return "portrait"
        case .portraitUpsideDown: return "portraitUpsideDown"
        case .landscapeLeft: return "landscapeLeft"
        case .landscapeRight: return "landscapeRight"
        case .faceUp: return "faceUp"          // screen up, camera pointing down at the wound
        case .faceDown: return "faceDown"
        default: return "unknown"
        }
    }

    private func trackingStateString(_ state: ARCamera.TrackingState) -> String {
        switch state {
        case .normal: return "normal"
        case .notAvailable: return "notAvailable"
        case .limited(let reason): return "limited:\(reason)"
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
    nonisolated func session(_ session: ARSession, didUpdate frame: ARFrame) {
        // Measure synchronously (the frame must not be retained), publish on the main actor.
        guard let g = estimator.update(with: frame) else { return }
        Task { @MainActor in
            self.guidance = g
        }
    }

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
    case imageConversionFailed

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
        case .imageConversionFailed:
            return "Could not read the camera image. Please try again."
        }
    }
}

// MARK: - UIImage from CVPixelBuffer

extension UIImage {
    /// One shared Core Image context: creating one per frame is expensive.
    private static let sharedCIContext = CIContext()

    convenience init?(pixelBuffer: CVPixelBuffer) {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = UIImage.sharedCIContext.createCGImage(ciImage, from: ciImage.extent) else {
            return nil
        }
        self.init(cgImage: cgImage)
    }
}
