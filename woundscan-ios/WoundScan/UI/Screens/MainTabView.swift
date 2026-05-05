import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            PortalTab(path: "/dashboard", title: "Dashboard")
                .tabItem { Label("Dashboard", systemImage: "square.grid.2x2") }

            PortalTab(path: "/patients", title: "Patients")
                .tabItem { Label("Patients", systemImage: "person.2.fill") }

            CaptureFlowView()
                .tabItem { Label("Capture", systemImage: "camera.viewfinder") }

            PortalTab(path: "/wounds", title: "Wounds")
                .tabItem { Label("Wounds", systemImage: "circle.hexagongrid.fill") }

            MoreMenu()
                .tabItem { Label("More", systemImage: "ellipsis.circle") }
        }
    }
}

private struct MoreMenu: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            List {
                Section("Portal") {
                    PortalRow(title: "Audit-safe notes", path: "/notes",      symbol: "doc.text.fill")
                    PortalRow(title: "Inventory & grafts", path: "/inventory", symbol: "shippingbox.fill")
                    PortalRow(title: "Route planner",      path: "/routes",    symbol: "map.fill")
                    PortalRow(title: "Orders",             path: "/orders",    symbol: "cart.fill")
                    PortalRow(title: "Claims",             path: "/claims",    symbol: "doc.richtext.fill")
                    PortalRow(title: "Compliance",         path: "/compliance",symbol: "checkmark.shield.fill")
                    PortalRow(title: "Reports",            path: "/reports",   symbol: "chart.bar.fill")
                    PortalRow(title: "Settings (portal)",  path: "/settings",  symbol: "slider.horizontal.3")
                }
                Section("Local") {
                    NavigationLink {
                        HistoryView()
                    } label: {
                        Label("Recent captures", systemImage: "clock.fill")
                    }
                    NavigationLink {
                        DeviceSettingsView()
                    } label: {
                        Label("Device settings", systemImage: "gearshape.fill")
                    }
                }
            }
            .navigationTitle("More")
        }
    }
}

private struct PortalRow: View {
    @EnvironmentObject var appState: AppState
    let title: String
    let path: String
    let symbol: String

    var body: some View {
        NavigationLink {
            PortalWebView(
                url: appState.portalURL.appendingPathComponent(path),
                sessionCookie: appState.session?.token
            )
            .ignoresSafeArea(edges: .bottom)
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
        } label: {
            Label(title, systemImage: symbol)
        }
    }
}

struct HistoryView: View {
    var body: some View {
        List {
            Text("Captures uploaded from this device appear here.")
                .foregroundStyle(.secondary)
        }
        .navigationTitle("Recent captures")
    }
}

struct DeviceSettingsView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Form {
            Section("Provider portal") {
                Link(destination: appState.portalURL) {
                    HStack {
                        Image(systemName: "rectangle.portrait.and.arrow.right.fill")
                        VStack(alignment: .leading) {
                            Text("Open portal in Safari").font(.headline)
                            Text(appState.portalURL.absoluteString)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
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
        .navigationTitle("Device settings")
    }
}
