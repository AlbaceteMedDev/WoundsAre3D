import Foundation

struct Wound: Identifiable, Codable, Equatable {
    let id: UUID
    var patientToken: String
    var anatomicLocation: String
    var woundType: String
    var onsetAt: Date?
    var createdAt: Date
    var notes: String
}

struct Patient: Identifiable, Codable, Equatable {
    let id: UUID
    var token: String
}
