import SwiftUI

/// Full-screen measurement view with embedded 3D wound viewer.
///
/// Renders scalar measurements (volume, area, depth) in a card stack at the
/// bottom while the reconstructed surface fills the upper portion. The 3D
/// viewer auto-rotates until the user touches it; gestures (pinch / pan /
/// orbit) are handled by SceneKit's default camera controller.
struct MeasurementDetailView: View {
    let measurement: MeasurementResult
    let api: APIClient

    @State private var meshData: Data?
    @State private var loadError: String?
    @State private var isLoading = true
    @State private var autoRotate = true
    @State private var showWireframe = false
    @State private var showsScale = true
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack(alignment: .top) {
            Color.black.ignoresSafeArea()
            content
            topBar
        }
        .preferredColorScheme(.dark)
        .task { await loadMesh() }
    }

    @ViewBuilder
    private var content: some View {
        if isLoading {
            VStack(spacing: 16) {
                ProgressView().scaleEffect(1.4).tint(.white)
                Text("Reconstructing surface…").foregroundStyle(.white.opacity(0.7))
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let mesh = meshData {
            VStack(spacing: 0) {
                ZStack(alignment: .bottomTrailing) {
                    WoundMeshView(meshOBJ: mesh, autoRotate: $autoRotate, showWireframe: $showWireframe)
                        .ignoresSafeArea(edges: .top)
                        .onTapGesture { autoRotate = false }
                    viewerControls
                        .padding(20)
                }
                metricsPanel
            }
        } else {
            VStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 38))
                    .foregroundStyle(.orange)
                Text(loadError ?? "Mesh unavailable")
                    .foregroundStyle(.white.opacity(0.8))
                Button("Retry") { Task { await loadMesh() } }
                    .buttonStyle(.borderedProminent)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var topBar: some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
                    .padding(10)
                    .background(.ultraThinMaterial, in: Circle())
            }
            Spacer()
            Text("Wound \(measurement.measurementId.uuidString.prefix(8))")
                .font(.headline)
                .foregroundStyle(.white)
                .padding(.horizontal, 14).padding(.vertical, 6)
                .background(.ultraThinMaterial, in: Capsule())
            Spacer()
            Color.clear.frame(width: 36, height: 36)
        }
        .padding(.horizontal)
    }

    private var viewerControls: some View {
        VStack(spacing: 10) {
            controlButton(system: autoRotate ? "pause.fill" : "play.fill") { autoRotate.toggle() }
            controlButton(system: showWireframe ? "square.grid.3x3.fill" : "square.grid.3x3") {
                showWireframe.toggle()
            }
        }
    }

    private func controlButton(system: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: system)
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(.ultraThinMaterial, in: Circle())
        }
    }

    private var metricsPanel: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                metricCard(
                    title: "Volume",
                    value: String(format: "%.2f", measurement.volume.mean),
                    unit: "cm³",
                    ci: ciString(measurement.volume)
                )
                metricCard(
                    title: "Surface area",
                    value: String(format: "%.1f", measurement.surfaceArea.mean),
                    unit: "cm²",
                    ci: ciString(measurement.surfaceArea)
                )
                metricCard(
                    title: "Max depth",
                    value: String(format: "%.2f", measurement.maxDepthCm),
                    unit: "cm"
                )
                metricCard(
                    title: "Mean depth",
                    value: String(format: "%.2f", measurement.meanDepthCm),
                    unit: "cm"
                )
                metricCard(
                    title: "Perimeter",
                    value: String(format: "%.1f", measurement.perimeterCm),
                    unit: "cm"
                )
                qualityCard
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
        }
        .background(
            LinearGradient(
                colors: [.black.opacity(0), .black.opacity(0.85), .black],
                startPoint: .top, endPoint: .bottom
            )
        )
    }

    private func metricCard(title: String, value: String, unit: String, ci: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.white.opacity(0.55))
            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 26, weight: .semibold, design: .rounded))
                    .foregroundStyle(.white)
                Text(unit)
                    .font(.callout.weight(.medium))
                    .foregroundStyle(.white.opacity(0.6))
            }
            if let ci {
                Text(ci)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.45))
            }
        }
        .padding(14)
        .frame(minWidth: 130, alignment: .leading)
        .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14).stroke(.white.opacity(0.08))
        )
    }

    private var qualityCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("QUALITY").font(.caption2.weight(.semibold)).foregroundStyle(.white.opacity(0.55))
            HStack(spacing: 8) {
                Text(measurement.quality.grade)
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundStyle(qualityColor)
                Text(measurement.quality.recommendation.replacingOccurrences(of: "_", with: " "))
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                    .lineLimit(2)
            }
        }
        .padding(14)
        .frame(minWidth: 170, alignment: .leading)
        .background(qualityColor.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(qualityColor.opacity(0.4)))
    }

    private var qualityColor: Color {
        switch measurement.quality.grade {
        case "A": .green
        case "B": .mint
        case "C": .yellow
        case "D": .orange
        default: .red
        }
    }

    private func ciString(_ v: UncertaintyValue) -> String {
        String(format: "95%% CI %.2f–%.2f", v.ci95Low, v.ci95High)
    }

    private func loadMesh() async {
        isLoading = true
        loadError = nil
        do {
            meshData = try await api.downloadMesh(measurementId: measurement.measurementId)
        } catch let APIError.http(code, body) {
            loadError = code == 404
                ? "This measurement doesn't have a 3D reconstruction yet."
                : "Failed to load mesh (HTTP \(code))"
            _ = body
        } catch {
            loadError = "Failed to load mesh: \(error.localizedDescription)"
        }
        isLoading = false
    }
}
