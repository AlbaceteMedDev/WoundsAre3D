import Foundation

/// Convenience wrapper that persists the auth session in the keychain.
@MainActor
final class AuthService {
    private let api: APIClient
    private let keychainKey = "com.albacetemeddev.woundscan.session"

    init(api: APIClient) {
        self.api = api
    }

    func signIn(email: String, password: String, totpCode: String) async throws -> AuthSession {
        let session = try await api.login(email: email, password: password, totpCode: totpCode)
        save(session)
        return session
    }

    func loadPersisted() -> AuthSession? {
        // Real impl uses Keychain Services. Stub here: return nil.
        nil
    }

    private func save(_ session: AuthSession) {
        // Real impl writes to Keychain. Stub here.
    }

    func signOut() {
        // Clear keychain entry.
    }
}
