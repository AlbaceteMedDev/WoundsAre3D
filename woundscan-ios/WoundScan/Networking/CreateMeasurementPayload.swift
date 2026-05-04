import Foundation

/// Wire-format measurement creation payload, matching the engine's
/// CreateMeasurementRequest schema 1:1.
struct CreateMeasurementPayload: Encodable {
    let woundId: UUID
    let capturedAt: Date
    let intrinsics: CameraIntrinsicsRecord
    let rgbS3Key: String
    let depthBurstS3Keys: [String]
    let poses: [CameraPoseRecord]
    let fiducials: [FiducialRecord]
    let fiducialMarkerSideMm: Double
    let fiducialSeparationMm: Double
    let boundary: BoundaryRecord
    let probeMeasurements: [ProbeRecord]
    let overlapDeltaCm: Double?
    let selectedProductIds: [String]
    let polarizedCaptureS3Key: String?
    let multispectralCaptureS3Keys: [String]
    let daysSinceLastVisit: Double?
    let lastVolumeCm3: Double?
    let lastAreaCm2: Double?

    enum CodingKeys: String, CodingKey {
        case woundId = "wound_id"
        case capturedAt = "captured_at"
        case intrinsics
        case rgbS3Key = "rgb_s3_key"
        case depthBurstS3Keys = "depth_burst_s3_keys"
        case poses
        case fiducials
        case fiducialMarkerSideMm = "fiducial_marker_side_mm"
        case fiducialSeparationMm = "fiducial_separation_mm"
        case boundary
        case probeMeasurements = "probe_measurements"
        case overlapDeltaCm = "overlap_delta_cm"
        case selectedProductIds = "selected_product_ids"
        case polarizedCaptureS3Key = "polarized_capture_s3_key"
        case multispectralCaptureS3Keys = "multispectral_capture_s3_keys"
        case daysSinceLastVisit = "days_since_last_visit"
        case lastVolumeCm3 = "last_volume_cm3"
        case lastAreaCm2 = "last_area_cm2"
    }
}
