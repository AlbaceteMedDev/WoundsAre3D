// ARViewContainer.swift
// AlbaceteMedDev

import SwiftUI
import ARKit
import SceneKit

struct ARViewContainer: UIViewRepresentable {

    let session: ARSession

    func makeUIView(context: Context) -> ARSCNView {
        let arView = ARSCNView()
        arView.session = session
        arView.automaticallyUpdatesLighting = false
        arView.scene = SCNScene()
        arView.antialiasingMode = .none
        arView.preferredFramesPerSecond = 30
        arView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        return arView
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {}
}
