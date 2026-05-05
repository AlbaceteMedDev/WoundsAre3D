import SwiftUI
import WebKit

/// Embeds the WoundScan web portal inside the iOS app. The portal is
/// the source of truth for the 11 non-capture tabs (Dashboard, Patient
/// Roster, Notes, Inventory, Routes, Orders, Claims, Compliance,
/// Reports, Settings, plus wound detail / 3-D viewer).
///
/// The view targets the portal URL derived from `AppState.apiBaseURL`:
/// localhost for dev, the bare host (api. → root) for prod.
struct PortalWebView: UIViewRepresentable {
    let url: URL
    /// Session token to pre-seed as a cookie so the portal sees the
    /// user as already-authenticated. `nil` falls back to the portal's
    /// own /login screen.
    let sessionCookie: String?

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        let view = WKWebView(frame: .zero, configuration: config)
        view.allowsBackForwardNavigationGestures = true
        view.navigationDelegate = context.coordinator
        view.scrollView.contentInsetAdjustmentBehavior = .always
        view.isOpaque = false
        view.backgroundColor = .systemBackground
        return view
    }

    func updateUIView(_ view: WKWebView, context: Context) {
        if context.coordinator.lastLoadedURL == url { return }
        context.coordinator.lastLoadedURL = url

        if let token = sessionCookie {
            seedSessionCookie(into: view, host: url.host ?? "localhost", token: token) {
                view.load(URLRequest(url: url))
            }
        } else {
            view.load(URLRequest(url: url))
        }
    }

    private func seedSessionCookie(
        into view: WKWebView,
        host: String,
        token: String,
        then: @escaping () -> Void
    ) {
        let cookie = HTTPCookie(properties: [
            .domain: host,
            .path: "/",
            .name: "ws_session",
            .value: token,
            .secure: false,
            .expires: Date().addingTimeInterval(60 * 60 * 12),
        ])
        guard let cookie else { then(); return }
        view.configuration.websiteDataStore.httpCookieStore.setCookie(cookie, completionHandler: then)
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var lastLoadedURL: URL?
    }
}

/// Wraps PortalWebView in a SwiftUI navigation container with a
/// progress shimmer.
struct PortalTab: View {
    @EnvironmentObject var appState: AppState
    let path: String
    let title: String

    var url: URL { appState.portalURL.appendingPathComponent(path) }

    var body: some View {
        NavigationStack {
            PortalWebView(url: url, sessionCookie: appState.session?.token)
                .ignoresSafeArea(edges: .bottom)
                .navigationTitle(title)
                .navigationBarTitleDisplayMode(.inline)
        }
    }
}
