// ScanAPIClient.swift
// AlbaceteMedDev
//
// Handles all communication with the wound scan backend API.

import Foundation

// MARK: - Response Models

struct PostScansResponse: Decodable {
    let scanId: String
    let uploadUrls: [String: String]
}

struct ScanStatusResponse: Decodable {
    let scanId: String
    let status: ScanStatus
}

enum ScanStatus: String, Decodable {
    case uploading = "UPLOADING"
    case processing = "PROCESSING"
    case complete = "COMPLETE"
    case failed = "FAILED"
}

struct ScanResultsResponse: Decodable {
    let scanId: String
    let status: String
    let measurements: Measurements
    let diagrams: DiagramURLs
    let narration: String
}

struct Measurements: Decodable {
    let lengthMm: Double
    let widthMm: Double
    let bedAreaCm2: Double
    let depthMm: Double
    let periWoundAreaCm2: Double

    enum CodingKeys: String, CodingKey {
        case lengthMm = "length_mm"
        case widthMm = "width_mm"
        case bedAreaCm2 = "bed_area_cm2"
        case depthMm = "depth_mm"
        case periWoundAreaCm2 = "peri_wound_area_cm2"
    }
}

struct DiagramURLs: Decodable {
    let diagramTop: String
    let diagramCross: String

    enum CodingKeys: String, CodingKey {
        case diagramTop = "diagram_top"
        case diagramCross = "diagram_cross"
    }
}

// MARK: - API Errors

enum ScanAPIError: LocalizedError {
    case invalidResponse
    case httpError(Int)
    case decodingError(Error)
    case uploadFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server."
        case .httpError(let code):
            return "Server returned HTTP \(code)."
        case .decodingError(let error):
            return "Failed to parse response: \(error.localizedDescription)"
        case .uploadFailed(let file):
            return "Failed to upload file: \(file)"
        }
    }
}

// MARK: - ScanAPIClient

actor ScanAPIClient {

    private let session: URLSession

    init(session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 120   // 2 min per request
        config.timeoutIntervalForResource = 300  // 5 min total
        return URLSession(configuration: config)
    }()) {
        self.session = session
    }

    // MARK: POST /scans

    /// Creates a new scan session and returns the scanId + 25 presigned PUT URLs.
    func createScan(sessionPayload: [String: Any] = [:]) async throws -> PostScansResponse {
        var request = URLRequest(url: AppConstants.API.scansURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: sessionPayload)

        let (data, response) = try await session.data(for: request)
        try validate(response: response)

        do {
            return try JSONDecoder().decode(PostScansResponse.self, from: data)
        } catch {
            throw ScanAPIError.decodingError(error)
        }
    }

    // MARK: GET /scans/{scanId}/status

    /// Polls the processing status for a given scan.
    func getScanStatus(scanId: String) async throws -> ScanStatusResponse {
        let request = URLRequest(url: AppConstants.API.statusURL(scanId: scanId))

        let (data, response) = try await session.data(for: request)
        try validate(response: response)

        do {
            return try JSONDecoder().decode(ScanStatusResponse.self, from: data)
        } catch {
            throw ScanAPIError.decodingError(error)
        }
    }

    // MARK: GET /scans/{scanId}/results

    /// Fetches the completed scan results including measurements and diagram URLs.
    func getScanResults(scanId: String) async throws -> ScanResultsResponse {
        let request = URLRequest(url: AppConstants.API.resultsURL(scanId: scanId))

        let (data, response) = try await session.data(for: request)
        try validate(response: response)

        do {
            return try JSONDecoder().decode(ScanResultsResponse.self, from: data)
        } catch {
            throw ScanAPIError.decodingError(error)
        }
    }

    // MARK: S3 Presigned PUT Upload

    /// Uploads raw data to S3 using a presigned PUT URL.
    /// Uses upload(for:from:) which correctly sends the body for PUT requests.
    /// Content-Type is intentionally omitted — presigned URLs are signed without it.
    func uploadFile(data: Data, to presignedURL: URL, contentType: String) async throws {
        var request = URLRequest(url: presignedURL)
        request.httpMethod = "PUT"

        let (responseData, response) = try await session.upload(for: request, from: data)
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            let code = (response as? HTTPURLResponse)?.statusCode ?? -1
            let body = String(data: responseData, encoding: .utf8) ?? "no body"
            print("[Upload] HTTP \(code) for \(presignedURL.lastPathComponent): \(body)")
            throw ScanAPIError.uploadFailed("\(presignedURL.lastPathComponent) (HTTP \(code))")
        }
    }

    // MARK: - Private Helpers

    private func validate(response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ScanAPIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw ScanAPIError.httpError(httpResponse.statusCode)
        }
    }
}
