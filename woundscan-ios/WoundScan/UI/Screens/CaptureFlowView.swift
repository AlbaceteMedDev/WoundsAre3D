import SwiftUI

/// The full capture flow: ARKit warmup → fiducial check → burst → probe entry
/// → boundary annotation → upload → result preview.
struct CaptureFlowView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var pipeline = CapturePipeline()
    @State private var step: Step = .warming

    enum Step: Equatable {
        case warming
        case capturing
        case probeEntry
        case boundary
        case uploading
        case result(MeasurementResult)
        case failed(String)
    }

    var body: some View {
        Group {
            switch step {
            case .warming:
                WarmupView(pipeline: pipeline) { step = .capturing }
            case .capturing:
                BurstCaptureView(pipeline: pipeline) {
                    step = .probeEntry
                }
            case .probeEntry:
                ProbeEntryView { _ in step = .boundary }
            case .boundary:
                BoundaryAnnotationView { _ in step = .uploading }
            case .uploading:
                UploadingView { result in step = .result(result) }
            case .result(let result):
                ResultView(result: result)
            case .failed(let message):
                Text("Capture failed: \(message)").padding()
            }
        }
        .task {
            await pipeline.start()
        }
    }
}

struct WarmupView: View {
    @ObservedObject var pipeline: CapturePipeline
    let onReady: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Warming up sensors…")
            Text("Hold the iPhone 30 cm from the wound; place fiducial sticker at the edge.")
                .font(.callout)
                .multilineTextAlignment(.center)
                .padding()

            if pipeline.stage == .ready {
                Button("Begin capture") { onReady() }
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding()
    }
}

struct BurstCaptureView: View {
    @ObservedObject var pipeline: CapturePipeline
    let onCaptured: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            ARLivePreview(session: pipeline.arkit.session)
                .frame(maxWidth: .infinity, maxHeight: 380)
                .clipShape(RoundedRectangle(cornerRadius: 12))

            HStack(spacing: 24) {
                MotionMeter(score: pipeline.arkit.motionScore)
                FiducialBadge(detected: pipeline.arkit.fiducialDetected)
            }

            Text("Frames: \(pipeline.arkit.frameCount) / 60")

            Button {
                Task {
                    await pipeline.captureBurst()
                    if case .done = pipeline.stage {
                        onCaptured()
                    }
                }
            } label: {
                Label("Capture", systemImage: "camera")
            }
            .buttonStyle(.borderedProminent)
            .disabled(pipeline.arkit.motionScore < 0.5)
        }
        .padding()
    }
}

struct ARLivePreview: UIViewRepresentable {
    let session: Any  // ARSession; UIViewRepresentable bridge

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.backgroundColor = .black
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {}
}

struct MotionMeter: View {
    let score: Float

    var body: some View {
        VStack {
            Image(systemName: "hand.raised.fill")
                .foregroundStyle(score > 0.7 ? .green : score > 0.4 ? .yellow : .red)
            Text("Motion")
                .font(.caption)
        }
    }
}

struct FiducialBadge: View {
    let detected: Bool

    var body: some View {
        VStack {
            Image(systemName: detected ? "checkmark.square.fill" : "square")
                .foregroundStyle(detected ? .green : .red)
            Text("Fiducial")
                .font(.caption)
        }
    }
}

struct ProbeEntryView: View {
    let onComplete: ([ProbeRecord]) -> Void
    @State private var anchors: [ProbeRecord] = []
    @State private var depthMm: Double = 5.0
    @State private var force: ProbeRecord.ForceCategory = .medium

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Probe entry").font(.title2).bold()
            Text("Tap each probe location on the photo, enter depth and force. Minimum 5 anchors recommended; 9+ ideal.")
                .font(.callout)
                .foregroundStyle(.secondary)

            HStack {
                Stepper("Depth: \(String(format: "%.1f", depthMm)) mm", value: $depthMm, in: 0...50, step: 0.5)
            }
            Picker("Force", selection: $force) {
                ForEach(ProbeRecord.ForceCategory.allCases, id: \.self) { f in
                    Text(f.rawValue.capitalized).tag(f)
                }
            }
            .pickerStyle(.segmented)

            Button("Add anchor") {
                anchors.append(
                    ProbeRecord(
                        xMm: 0, yMm: 0,
                        depthMm: depthMm,
                        forceCategory: force,
                        probeType: .cottonTip,
                        autoDetected: false,
                        notes: ""
                    )
                )
            }

            List(anchors) { p in
                HStack {
                    Text("(\(String(format: "%.1f", p.xMm)), \(String(format: "%.1f", p.yMm))) mm")
                    Spacer()
                    Text("\(String(format: "%.1f", p.depthMm)) mm").foregroundStyle(.secondary)
                }
            }

            Button("Continue (\(anchors.count) anchors)") {
                onComplete(anchors)
            }
            .buttonStyle(.borderedProminent)
            .disabled(anchors.count < 5)
        }
        .padding()
    }
}

struct BoundaryAnnotationView: View {
    let onComplete: (BoundaryRecord) -> Void
    @State private var vertices: [[Double]] = []

    var body: some View {
        VStack {
            Text("Boundary annotation").font(.title2).bold()
            Text("ML proposes the wound boundary. Edit vertices as needed.")
                .font(.callout)
                .foregroundStyle(.secondary)

            // Placeholder: real implementation overlays an interactive polygon
            // editor on the captured RGB photo.
            Rectangle()
                .fill(.gray.opacity(0.2))
                .frame(height: 320)

            Button("Use proposed boundary") {
                let circle = (0..<24).map { i -> [Double] in
                    let theta = 2.0 * .pi * Double(i) / 24.0
                    return [20.0 * cos(theta), 20.0 * sin(theta)]
                }
                onComplete(BoundaryRecord(verticesMm: circle))
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}

struct UploadingView: View {
    let onResult: (MeasurementResult) -> Void

    var body: some View {
        VStack {
            ProgressView()
            Text("Uploading and processing…").padding()
        }
    }
}

struct ResultView: View {
    let result: MeasurementResult
    @EnvironmentObject var appState: AppState
    @State private var show3D = false

    var body: some View {
        Form {
            Section {
                Button {
                    show3D = true
                } label: {
                    HStack {
                        Image(systemName: "cube.transparent.fill")
                            .font(.title3)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("View 3D reconstruction").font(.headline)
                            Text("Rotate, zoom, and inspect the wound surface")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(.tertiary)
                    }
                    .padding(.vertical, 4)
                }
            }
            Section("Measurements") {
                Text("Volume: \(String(format: "%.2f", result.volume.mean)) cm³ (95% CI \(String(format: "%.2f", result.volume.ci95Low))–\(String(format: "%.2f", result.volume.ci95High)))")
                Text("3D SA: \(String(format: "%.2f", result.surfaceArea.mean)) cm²")
                Text("Max depth: \(String(format: "%.2f", result.maxDepthCm)) cm")
            }
            Section("Quality") {
                Text("Grade: \(result.quality.grade)")
                Text("Score: \(String(format: "%.2f", result.quality.overallScore))")
            }
            Section("Graft") {
                ForEach(result.graftRecommendations) { rec in
                    VStack(alignment: .leading) {
                        Text(rec.productName).bold()
                        Text(rec.rationale).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            if !result.plausibilityWarnings.isEmpty {
                Section("Plausibility") {
                    ForEach(result.plausibilityWarnings, id: \.self) { Text($0) }
                }
            }
        }
        .navigationTitle("Result")
        .fullScreenCover(isPresented: $show3D) {
            let api = APIClient(baseURL: appState.apiBaseURL)
            let _ = api.setToken(appState.session?.token)
            MeasurementDetailView(measurement: result, api: api)
        }
    }
}
