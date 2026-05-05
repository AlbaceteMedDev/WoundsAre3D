import Foundation

/// Fetches reconstructed wound meshes from the engine API.
@MainActor
final class MeshService {
    private let api: APIClient

    init(api: APIClient) { self.api = api }

    func fetchMesh(measurementId: UUID) async throws -> Data {
        try await api.downloadMesh(measurementId: measurementId)
    }
}
