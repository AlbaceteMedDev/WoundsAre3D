import Foundation
import simd

/// A camera intrinsic record matching the engine's CameraIntrinsicsInput.
struct CameraIntrinsicsRecord: Codable, Equatable {
    var fx: Double
    var fy: Double
    var cx: Double
    var cy: Double
    var width: Int
    var height: Int
}

/// 6-DoF camera pose for a single frame.
struct CameraPoseRecord: Codable, Equatable {
    var positionM: [Double] // [x, y, z]
    var rotationQuat: [Double] // [x, y, z, w]
    var timestampS: Double
}

/// Detected ArUco fiducial in image-space + recovered marker pose.
struct FiducialRecord: Codable, Equatable {
    var markerId: Int
    var cornersPix: [[Double]] // 4 x 2
    var rvec: [Double] // 3
    var tvec: [Double] // 3
    var reprojectionErrorPix: Double
}

/// Probe measurement entered by clinician.
struct ProbeRecord: Codable, Equatable, Identifiable {
    var id: UUID = UUID()
    var xMm: Double
    var yMm: Double
    var depthMm: Double
    var forceCategory: ForceCategory
    var probeType: ProbeType
    var autoDetected: Bool
    var notes: String

    enum ForceCategory: String, Codable, CaseIterable {
        case light
        case medium
        case firm
    }

    enum ProbeType: String, Codable, CaseIterable {
        case cottonTip = "cotton_tip"
        case plasticGauge = "plastic_gauge"
        case kundinGauge = "kundin_gauge"
        case other
    }
}

/// Wound boundary polygon (clinician annotation).
struct BoundaryRecord: Codable, Equatable {
    /// Vertices in mm in the wound-local frame.
    var verticesMm: [[Double]]
}

/// All artifacts collected during a single capture session.
struct CaptureSessionArtifacts {
    let woundId: UUID
    let capturedAt: Date
    let intrinsics: CameraIntrinsicsRecord
    var rgbS3Key: String?
    var depthBurstS3Keys: [String] = []
    var poses: [CameraPoseRecord] = []
    var fiducials: [FiducialRecord] = []
    var fiducialMarkerSideMm: Double = 10.0
    var fiducialSeparationMm: Double = 50.0
    var boundary: BoundaryRecord?
    var probes: [ProbeRecord] = []
    var overlapDeltaCm: Double?
    var selectedProductIds: [String] = []
    var polarizedCaptureS3Key: String?
    var multispectralCaptureS3Keys: [String] = []
    var daysSinceLastVisit: Double?
    var lastVolumeCm3: Double?
    var lastAreaCm2: Double?
}
