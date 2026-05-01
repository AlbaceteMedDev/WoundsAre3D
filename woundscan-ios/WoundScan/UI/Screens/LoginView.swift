import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @State private var email = ""
    @State private var password = ""
    @State private var totpCode = ""
    @State private var error: String?
    @State private var isLoading = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Sign in") {
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                    SecureField("Password", text: $password)
                    TextField("6-digit code", text: $totpCode)
                        .keyboardType(.numberPad)
                }
                if let error {
                    Text(error).foregroundStyle(.red)
                }
                Button {
                    Task { await signIn() }
                } label: {
                    if isLoading {
                        ProgressView()
                    } else {
                        Text("Sign in")
                    }
                }
                .disabled(email.isEmpty || password.isEmpty || totpCode.count < 6 || isLoading)
            }
            .navigationTitle("WoundScan")
        }
    }

    func signIn() async {
        isLoading = true
        defer { isLoading = false }
        let api = APIClient(baseURL: appState.apiBaseURL)
        do {
            let session = try await api.login(email: email, password: password, totpCode: totpCode)
            appState.signIn(session)
        } catch {
            self.error = "Sign-in failed. Verify credentials and TOTP code."
        }
    }
}
