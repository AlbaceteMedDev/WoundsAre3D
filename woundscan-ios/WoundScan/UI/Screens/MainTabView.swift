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

    var body: some View {
        NavigationStack {
            Form {
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
