import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            WoundListView()
                .tabItem { Label("Wounds", systemImage: "list.bullet") }
            CaptureFlowView()
                .tabItem { Label("Capture", systemImage: "camera") }
            HistoryView()
                .tabItem { Label("History", systemImage: "clock") }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
        }
    }
}

struct WoundListView: View {
    var body: some View {
        NavigationStack {
            List {
                Text("Patient: opaque-token-1234")
                Text("Wound: right plantar foot, DFU")
            }
            .navigationTitle("Wounds")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    NavigationLink("New") { CaptureFlowView() }
                }
            }
        }
    }
}

struct HistoryView: View {
    var body: some View {
        NavigationStack {
            List {
                Text("Recent measurements show here")
            }
            .navigationTitle("History")
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    var portalURL: URL {
        // Resolve "https://api.host" or "http://localhost:8000" → portal origin.
        // Local dev portal lives on :3000 by convention.
        var host = appState.apiBaseURL.host ?? "localhost"
        let scheme = appState.apiBaseURL.scheme ?? "http"
        if host == "localhost" || host == "127.0.0.1" {
            return URL(string: "http://\(host):3000")!
        }
        if host.hasPrefix("api.") { host = String(host.dropFirst(4)) }
        return URL(string: "\(scheme)://\(host)")!
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Provider portal") {
                    Link(destination: portalURL) {
                        HStack {
                            Image(systemName: "rectangle.portrait.and.arrow.right.fill")
                            VStack(alignment: .leading) {
                                Text("Open web portal").font(.headline)
                                Text(portalURL.absoluteString)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    Text("Patient roster, claims, compliance, reports, and notes live in the web portal — open it on this phone or any browser.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Account") {
                    Text("Role: \(appState.session?.role ?? "—")")
                    Button("Sign out", role: .destructive) {
                        appState.signOut()
                    }
                }
                Section("Environment") {
                    Text("API: \(appState.apiBaseURL.absoluteString)")
                }
                Section("About") {
                    Text("WoundScan iOS v1.0.0")
                    Text("Clinical Decision Support — not for diagnostic use")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
        }
    }
}
