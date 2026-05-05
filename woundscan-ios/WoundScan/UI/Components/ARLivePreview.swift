import ARKit
import SceneKit
import SwiftUI

/// Live AR camera feed bound to an existing `ARSession`.
///
/// Renders the back camera feed via `ARSCNView` so the operator can
/// frame the wound. Lighting estimation is on, plane detection is off
/// (we want the depth sensor's surface, not horizontal/vertical planes).
struct ARLivePreview: UIViewRepresentable {
    let session: ARSession

    func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView()
        view.session = session
        view.automaticallyUpdatesLighting = true
        view.scene = SCNScene()
        view.backgroundColor = .black
        view.contentMode = .scaleAspectFill
        view.preferredFramesPerSecond = 60
        return view
    }

    func updateUIView(_ view: ARSCNView, context: Context) {
        // Re-bind in case the parent recreates the session.
        if view.session !== session {
            view.session = session
        }
    }
}
