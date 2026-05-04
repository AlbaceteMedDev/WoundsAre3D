import Foundation
import Combine

/// App-wide state: auth token, signed-in clinician, environment.
@MainActor
final class AppState: ObservableObject {
    @Published var session: AuthSession?
    @Published var apiBaseURL: URL = URL(string: "https://api.dev.woundscan.local")!

    var isAuthenticated: Bool {
        session?.isValid ?? false
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
