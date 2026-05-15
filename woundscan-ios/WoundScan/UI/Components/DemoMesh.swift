import Foundation

/// Generates a synthetic wound-bed Wavefront OBJ in memory.
///
/// Produces the same Gaussian-depression surface as the web's
/// `/public/demo-wound.obj` (41 × 41 grid, ~40 mm × 40 mm extent, ~12 mm
/// max depth). Used by `MeshDemoView` so the 3D viewer is reachable
/// without a real backend / measurement upload — design reviews,
/// stakeholder demos, and quick post-build smoke checks.
enum DemoMesh {
    static func makeOBJ(resolution n: Int = 41, extentMM: Float = 40, depthMM: Float = 12) -> Data {
        var lines: [String] = [
            "# WoundScan synthetic demo mesh (\(n)×\(n) grid, ±\(extentMM/2)mm, max depth \(depthMM)mm)"
        ]
        let nf = Float(n - 1)
        for i in 0..<n {
            let y = -extentMM / 2 + extentMM * Float(i) / nf
            for j in 0..<n {
                let x = -extentMM / 2 + extentMM * Float(j) / nf
                let r2 = (x * x + y * y) / 144.0  // sigma ≈ 12mm
                let base = -depthMM * expf(-r2)
                let ripple = 0.6 * sinf(0.35 * x) * cosf(0.35 * y) * expf(-r2 * 0.8)
                let z = base + ripple
                lines.append("v \(String(format: "%.4f", x)) \(String(format: "%.4f", y)) \(String(format: "%.4f", z))")
            }
        }
        for i in 0..<(n - 1) {
            for j in 0..<(n - 1) {
                let a = i * n + j + 1
                let b = i * n + j + 2
                let c = (i + 1) * n + j + 2
                let d = (i + 1) * n + j + 1
                lines.append("f \(a) \(b) \(c)")
                lines.append("f \(a) \(c) \(d)")
            }
        }
        return Data((lines.joined(separator: "\n") + "\n").utf8)
    }
}
