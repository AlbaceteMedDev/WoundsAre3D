import SceneKit
import SwiftUI

/// Interactive 3D viewer for a reconstructed wound surface.
///
/// Loads a Wavefront OBJ mesh from raw bytes, computes per-vertex normals
/// and depth-mapped colors (cool = shallow, warm = deep), and presents it
/// inside a SceneKit view with native gestures (pinch, pan, rotate) and
/// optional auto-rotate.
///
/// The mesh is in millimeters in the wound-local frame; we re-center it on
/// load so any wound sits at the world origin regardless of where its
/// boundary polygon was in the request.
struct WoundMeshView: UIViewRepresentable {
    let meshOBJ: Data
    @Binding var autoRotate: Bool
    @Binding var showWireframe: Bool

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = UIColor(white: 0.06, alpha: 1.0)
        view.allowsCameraControl = true
        view.defaultCameraController.interactionMode = .orbitTurntable
        view.defaultCameraController.inertiaEnabled = true
        view.antialiasingMode = .multisampling4X
        view.autoenablesDefaultLighting = false
        view.preferredFramesPerSecond = 60

        let scene = SCNScene()
        scene.background.contents = UIColor(white: 0.06, alpha: 1.0)
        view.scene = scene

        configureLighting(scene: scene)
        if let meshNode = buildMeshNode(from: meshOBJ) {
            scene.rootNode.addChildNode(meshNode)
            context.coordinator.meshNode = meshNode
            framePOV(view: view, around: meshNode)
        }
        if autoRotate { startAutoRotate(view: view, coordinator: context.coordinator) }
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        guard let meshNode = context.coordinator.meshNode else { return }

        meshNode.geometry?.firstMaterial?.fillMode = showWireframe ? .lines : .fill

        let isRotating = context.coordinator.rotationAction != nil
        if autoRotate && !isRotating {
            startAutoRotate(view: view, coordinator: context.coordinator)
        } else if !autoRotate && isRotating {
            meshNode.removeAction(forKey: "autorotate")
            context.coordinator.rotationAction = nil
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        var meshNode: SCNNode?
        var rotationAction: SCNAction?
    }

    private func startAutoRotate(view: SCNView, coordinator: Coordinator) {
        guard let mesh = coordinator.meshNode else { return }
        let spin = SCNAction.repeatForever(
            SCNAction.rotateBy(x: 0, y: .pi * 2, z: 0, duration: 16)
        )
        mesh.runAction(spin, forKey: "autorotate")
        coordinator.rotationAction = spin
    }

    private func framePOV(view: SCNView, around node: SCNNode) {
        let (minVec, maxVec) = node.boundingBox
        let size = SCNVector3(maxVec.x - minVec.x, maxVec.y - minVec.y, maxVec.z - minVec.z)
        let radius = max(size.x, max(size.y, size.z)) * 1.4
        let camera = SCNCamera()
        camera.fieldOfView = 35
        camera.zNear = 0.1
        camera.zFar = Double(radius * 20)
        let camNode = SCNNode()
        camNode.camera = camera
        camNode.position = SCNVector3(0, -radius * 0.6, radius * 1.4)
        camNode.eulerAngles = SCNVector3(Float.pi * 0.25, 0, 0)
        view.scene?.rootNode.addChildNode(camNode)
        view.pointOfView = camNode
    }

    private func configureLighting(scene: SCNScene) {
        // Soft ambient so shadows don't crush detail.
        let ambient = SCNLight()
        ambient.type = .ambient
        ambient.color = UIColor(white: 0.35, alpha: 1.0)
        let ambientNode = SCNNode()
        ambientNode.light = ambient
        scene.rootNode.addChildNode(ambientNode)

        // Key light: warm, from upper-left.
        let key = SCNLight()
        key.type = .directional
        key.color = UIColor(red: 1.0, green: 0.94, blue: 0.86, alpha: 1.0)
        key.intensity = 900
        let keyNode = SCNNode()
        keyNode.light = key
        keyNode.eulerAngles = SCNVector3(-Float.pi * 0.4, -Float.pi * 0.25, 0)
        scene.rootNode.addChildNode(keyNode)

        // Fill light: cool, from lower-right, gentler.
        let fill = SCNLight()
        fill.type = .directional
        fill.color = UIColor(red: 0.7, green: 0.82, blue: 1.0, alpha: 1.0)
        fill.intensity = 350
        let fillNode = SCNNode()
        fillNode.light = fill
        fillNode.eulerAngles = SCNVector3(-Float.pi * 0.15, Float.pi * 0.4, 0)
        scene.rootNode.addChildNode(fillNode)
    }

    // MARK: - OBJ parsing

    /// Parse a minimal Wavefront OBJ (only `v` and `f` lines), build SCNGeometry
    /// with per-vertex depth-coded colors and smooth normals, return as a
    /// centered, oriented SCNNode.
    private func buildMeshNode(from data: Data) -> SCNNode? {
        guard let text = String(data: data, encoding: .utf8) else { return nil }
        var positions: [SIMD3<Float>] = []
        var indices: [UInt32] = []

        text.enumerateLines { line, _ in
            if line.hasPrefix("v ") {
                let parts = line.split(separator: " ")
                if parts.count >= 4,
                   let x = Float(parts[1]), let y = Float(parts[2]), let z = Float(parts[3]) {
                    positions.append(SIMD3(x, y, z))
                }
            } else if line.hasPrefix("f ") {
                let parts = line.split(separator: " ").dropFirst()
                let verts: [UInt32] = parts.compactMap {
                    let head = $0.split(separator: "/").first.map(String.init) ?? String($0)
                    return UInt32(head).map { $0 - 1 }
                }
                if verts.count == 3 {
                    indices.append(verts[0]); indices.append(verts[1]); indices.append(verts[2])
                } else if verts.count == 4 {
                    indices.append(verts[0]); indices.append(verts[1]); indices.append(verts[2])
                    indices.append(verts[0]); indices.append(verts[2]); indices.append(verts[3])
                }
            }
        }
        guard !positions.isEmpty, !indices.isEmpty else { return nil }

        // Re-center on world origin and flip Z so the wound sinks into the screen.
        let bbMin = positions.reduce(positions[0]) { simd_min($0, $1) }
        let bbMax = positions.reduce(positions[0]) { simd_max($0, $1) }
        let center = (bbMin + bbMax) * 0.5
        let recentered = positions.map { p -> SIMD3<Float> in
            SIMD3(p.x - center.x, p.y - center.y, -(p.z - bbMin.z))
        }

        // Depth-coded colors: 0 = cool blue (shallow / rim), 1 = warm crimson (deep).
        let zMin: Float = recentered.map(\.z).min() ?? 0
        let zMax: Float = recentered.map(\.z).max() ?? 1
        let zSpan = max(zMax - zMin, 0.001)
        let colors: [SIMD4<Float>] = recentered.map { p in
            let t = (p.z - zMin) / zSpan
            return depthGradient(t)
        }

        // Smooth per-vertex normals: average of incident face normals.
        var normals = [SIMD3<Float>](repeating: SIMD3(0, 0, 0), count: recentered.count)
        for k in stride(from: 0, to: indices.count, by: 3) {
            let a = Int(indices[k]), b = Int(indices[k + 1]), c = Int(indices[k + 2])
            let n = simd_normalize(simd_cross(recentered[b] - recentered[a], recentered[c] - recentered[a]))
            normals[a] += n; normals[b] += n; normals[c] += n
        }
        for i in normals.indices { normals[i] = simd_normalize(normals[i]) }

        let posSource = SCNGeometrySource(vertices: recentered.map { SCNVector3($0) })
        let normalSource = SCNGeometrySource(normals: normals.map { SCNVector3($0) })
        let colorData = Data(bytes: colors, count: MemoryLayout<SIMD4<Float>>.stride * colors.count)
        let colorSource = SCNGeometrySource(
            data: colorData,
            semantic: .color,
            vectorCount: colors.count,
            usesFloatComponents: true,
            componentsPerVector: 4,
            bytesPerComponent: MemoryLayout<Float>.size,
            dataOffset: 0,
            dataStride: MemoryLayout<SIMD4<Float>>.stride
        )
        let indexData = indices.withUnsafeBufferPointer { Data(buffer: $0) }
        let element = SCNGeometryElement(
            data: indexData,
            primitiveType: .triangles,
            primitiveCount: indices.count / 3,
            bytesPerIndex: MemoryLayout<UInt32>.size
        )

        let geometry = SCNGeometry(
            sources: [posSource, normalSource, colorSource],
            elements: [element]
        )
        let mat = SCNMaterial()
        mat.lightingModel = .physicallyBased
        mat.diffuse.contents = UIColor.white
        mat.metalness.contents = 0.0
        mat.roughness.contents = 0.55
        mat.isDoubleSided = true
        geometry.firstMaterial = mat

        let node = SCNNode(geometry: geometry)
        // Scale millimeters down so the bounding sphere is roughly unit-sized;
        // SceneKit defaults to meters and our mesh is in millimeters.
        let extent = max(bbMax.x - bbMin.x, max(bbMax.y - bbMin.y, bbMax.z - bbMin.z))
        let unit = extent > 0 ? 1.0 / extent * 60 : 1.0
        node.scale = SCNVector3(unit, unit, unit)
        return node
    }

    /// Cool-to-warm depth gradient (similar to viridis turned medical-grade).
    /// t=0 → blue-grey rim, t=0.5 → magenta, t=1 → deep crimson.
    private func depthGradient(_ t: Float) -> SIMD4<Float> {
        let stops: [(Float, SIMD3<Float>)] = [
            (0.0, SIMD3(0.20, 0.34, 0.55)),
            (0.35, SIMD3(0.62, 0.30, 0.55)),
            (0.7, SIMD3(0.86, 0.27, 0.36)),
            (1.0, SIMD3(0.55, 0.05, 0.10)),
        ]
        for i in 0..<(stops.count - 1) {
            let (t0, c0) = stops[i]
            let (t1, c1) = stops[i + 1]
            if t <= t1 {
                let u = (t - t0) / max(t1 - t0, 0.0001)
                let c = simd_mix(c0, c1, SIMD3(u, u, u))
                return SIMD4(c.x, c.y, c.z, 1.0)
            }
        }
        let last = stops.last!.1
        return SIMD4(last.x, last.y, last.z, 1.0)
    }
}
