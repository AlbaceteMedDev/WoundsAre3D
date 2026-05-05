import Foundation
import Combine

/// App-wide state: auth token, signed-in clinician, environment.
@MainActor
final class AppState: ObservableObject {
    @Published var session: AuthSession?
    @Published var apiBaseURL: URL = AppState.defaultAPIBaseURL()

    static func defaultAPIBaseURL() -> URL {
        if let override = Bundle.main.object(forInfoDictionaryKey: "WS_API_BASE_URL") as? String,
           let url = URL(string: override) {
            return url
        }
        return URL(string: "https://woundscan.albacetemeddev.com")!
    }

    var isAuthenticated: Bool {
        session?.isValid ?? false
    }

    /// Portal origin derived from the API base URL. Local dev → :3000,
    /// production → strip the api. prefix so https://api.host → https://host.
    var portalURL: URL {
        var host = apiBaseURL.host ?? "localhost"
        let scheme = apiBaseURL.scheme ?? "https"
        if host == "localhost" || host == "127.0.0.1" {
            return URL(string: "http://\(host):3000")!
        }
        if host.hasPrefix("api.") { host = String(host.dropFirst(4)) }
        return URL(string: "\(scheme)://\(host)")!
    }

    func signIn(_ session: AuthSession) {
        self.session = session
    }

    func signOut() {
        session = nil
    }
}

struct AuthSession: Codable, Equatable {
    let token: String
    let expiresAt: Date
    let role: String

    var isValid: Bool {
        Date() < expiresAt
    }
}
