import SwiftUI

/// Public preview of the 3D mesh viewer using a procedurally generated
/// synthetic wound bed. Reachable from `More → Local → 3D mesh demo`.
/// Mirrors the web `/demo` route — no backend or auth required.
struct MeshDemoView: View {
    @State private var autoRotate: Bool = true
    @State private var showWireframe: Bool = false
    private let mesh: Data = DemoMesh.makeOBJ()

    var body: some View {
        VStack(spacing: 0) {
            WoundMeshView(meshOBJ: mesh, autoRotate: $autoRotate, showWireframe: $showWireframe)
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            HStack(spacing: 16) {
                Toggle(isOn: $autoRotate) {
                    Label("Auto-rotate", systemImage: "arrow.triangle.2.circlepath")
                        .font(.footnote)
                }
                .toggleStyle(.switch)

                Toggle(isOn: $showWireframe) {
                    Label("Wireframe", systemImage: "square.grid.3x3")
                        .font(.footnote)
                }
                .toggleStyle(.switch)
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
            .background(.thinMaterial)
        }
        .ignoresSafeArea(edges: .top)
        .navigationTitle("3D mesh demo")
        .navigationBarTitleDisplayMode(.inline)
    }
}
