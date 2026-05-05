import Foundation

enum APIError: Error {
    case http(Int, String)
    case transport(Error)
    case decoding(Error)
    case noToken
}

/// Async HTTP client for the WoundScan engine API.
@MainActor
final class APIClient {
    private let baseURL: URL
    private let session: URLSession
    private var token: String?

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func setToken(_ token: String?) {
        self.token = token
    }

    func login(email: String, password: String, totpCode: String) async throws -> AuthSession {
        struct Req: Encodable {
            let email: String
            let password: String
            let totp_code: String
        }
        struct Res: Decodable {
            let token: String
            let expires_at: Date
            let role: String
        }

        let req = Req(email: email, password: password, totp_code: totpCode)
        let body = try JSONEncoder.iso.encode(req)
        let res: Res = try await request("/auth/login", method: "POST", body: body, requireAuth: false)
        let session = AuthSession(token: res.token, expiresAt: res.expires_at, role: res.role)
        setToken(session.token)
        return session
    }

    func presignedUploads(woundId: UUID, artifactType: String, count: Int) async throws -> [PresignedUpload] {
        struct Req: Encodable {
            let wound_id: UUID
            let artifact_type: String
            let file_count: Int
        }
        struct Res: Decodable {
            let uploads: [PresignedUpload]
        }
        let body = try JSONEncoder.iso.encode(Req(wound_id: woundId, artifact_type: artifactType, file_count: count))
        let res: Res = try await request("/uploads/presigned", method: "POST", body: body)
        return res.uploads
    }

    func createMeasurement(_ payload: CreateMeasurementPayload) async throws -> MeasurementResult {
        let body = try JSONEncoder.iso.encode(payload)
        return try await request("/measurements", method: "POST", body: body)
    }

    func getMeasurement(id: UUID) async throws -> MeasurementResult {
        try await request("/measurements/\(id.uuidString)", method: "GET")
    }

    private func request<T: Decodable>(
        _ path: String,
        method: String,
        body: Data? = nil,
        requireAuth: Bool = true
    ) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if requireAuth {
            guard let token else { throw APIError.noToken }
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body { req.httpBody = body }

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.http(-1, "no response")
        }
        guard (200..<300).contains(http.statusCode) else {
            let bodyStr = String(data: data, encoding: .utf8) ?? ""
            throw APIError.http(http.statusCode, bodyStr)
        }
        do {
            return try JSONDecoder.iso.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}

struct PresignedUpload: Codable {
    let s3Key: String
    let uploadURL: String
    let method: String

    enum CodingKeys: String, CodingKey {
        case s3Key = "s3_key"
        case uploadURL = "upload_url"
        case method
    }
}

extension JSONEncoder {
    static let iso: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()
}

extension JSONDecoder {
    static let iso: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}
