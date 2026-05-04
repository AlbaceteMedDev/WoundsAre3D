import Foundation

struct MeasurementResult: Codable, Identifiable, Equatable {
    var id: UUID { measurementId }

    let measurementId: UUID
    let woundId: UUID
    let capturedAt: Date
    let processedAt: Date
    let processingDurationMs: Double
    let volume: UncertaintyValue
    let surfaceArea: UncertaintyValue
    let maxDepthCm: Double
    let meanDepthCm: Double
    let perimeterCm: Double
    let footprintAreaCm2: Double
    let quality: QualityReport
    let graftRecommendations: [GraftRecommendationOut]
    let plausibilityPassed: Bool
    let plausibilityWarnings: [String]
    let temporalWarnings: [String]
    let pdfS3Key: String

    enum CodingKeys: String, CodingKey {
        case measurementId = "measurement_id"
        case woundId = "wound_id"
        case capturedAt = "captured_at"
        case processedAt = "processed_at"
        case processingDurationMs = "processing_duration_ms"
        case volume
        case surfaceArea = "surface_area"
        case maxDepthCm = "max_depth_cm"
        case meanDepthCm = "mean_depth_cm"
        case perimeterCm = "perimeter_cm"
        case footprintAreaCm2 = "footprint_area_cm2"
        case quality
        case graftRecommendations = "graft_recommendations"
        case plausibilityPassed = "plausibility_passed"
        case plausibilityWarnings = "plausibility_warnings"
        case temporalWarnings = "temporal_warnings"
        case pdfS3Key = "pdf_s3_key"
    }
}

struct UncertaintyValue: Codable, Equatable {
    let mean: Double
    let std: Double
    let ci95Low: Double
    let ci95High: Double

    enum CodingKeys: String, CodingKey {
        case mean
        case std
        case ci95Low = "ci_95_low"
        case ci95High = "ci_95_high"
    }
}

struct QualityReport: Codable, Equatable {
    let grade: String
    let overallScore: Double
    let components: [String: Double]
    let recommendation: String

    enum CodingKeys: String, CodingKey {
        case grade
        case overallScore = "overall_score"
        case components
        case recommendation
    }
}

struct GraftRecommendationOut: Codable, Equatable, Identifiable {
    var id: String { productId }
    let productId: String
    let productName: String
    let overlapDeltaCm: Double
    let requiredCm2: Double
    let selectedSizeCm2: Double?
    let rationale: String

    enum CodingKeys: String, CodingKey {
        case productId = "product_id"
        case productName = "product_name"
        case overlapDeltaCm = "overlap_delta_cm"
        case requiredCm2 = "required_cm2"
        case selectedSizeCm2 = "selected_size_cm2"
        case rationale
    }
}
