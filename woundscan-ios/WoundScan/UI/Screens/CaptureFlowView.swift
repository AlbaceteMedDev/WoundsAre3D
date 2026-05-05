import ARKit
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

// MARK: – Warmup

struct WarmupView: View {
    @ObservedObject var pipeline: CapturePipeline
    let onReady: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ZStack {
                ARLivePreview(session: pipeline.arkit.session)
                    .ignoresSafeArea()

                VStack {
                    Spacer()
                    GuidancePanel(arkit: pipeline.arkit)
                    Spacer()
                    InstructionCard()
                        .padding(.horizontal)
                        .padding(.bottom, 12)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            Button {
                onReady()
            } label: {
                Label("Start capture", systemImage: "camera.viewfinder")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .disabled(pipeline.stage != .ready)
            .padding(.horizontal)
            .padding(.bottom, 12)
        }
        .onAppear {
            Task { await pipeline.start() }
        }
    }
}

private struct InstructionCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("How to capture a clean scan", systemImage: "info.circle.fill")
                .font(.caption.weight(.semibold))
            Text("• Hold the phone **30 cm above** the wound (parallel to skin).")
            Text("• Place the **calibration sticker** at the wound edge.")
            Text("• Keep the phone **steady** until the indicator turns green.")
            Text("• Avoid harsh shadows or specular glare.")
        }
        .font(.caption)
        .foregroundStyle(.white)
        .padding(12)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: – Burst capture

struct BurstCaptureView: View {
    @ObservedObject var pipeline: CapturePipeline
    let onCaptured: () -> Void

    var canCapture: Bool {
        pipeline.arkit.motionScore >= 0.6 &&
        (pipeline.arkit.distanceMm.map { $0 >= 200 && $0 <= 400 } ?? false) &&
        abs(pipeline.arkit.pitchDeg - 90) <= 25 &&
        isTrackingNormal(pipeline.arkit.trackingState)
    }

    var body: some View {
        ZStack {
            ARLivePreview(session: pipeline.arkit.session)
                .ignoresSafeArea()

            // Centre reticle to aim at the wound bed
            Reticle(active: canCapture)

            VStack {
                Spacer()
                GuidancePanel(arkit: pipeline.arkit)
                if case .capturing(let progress) = pipeline.stage {
                    ProgressView(value: progress)
                        .tint(.white)
                        .padding(.horizontal)
                        .padding(.top, 8)
                }
                BurstActionRow(canCapture: canCapture, frameCount: pipeline.arkit.frameCount) {
                    Task {
                        await pipeline.captureBurst()
                        if case .done = pipeline.stage { onCaptured() }
                    }
                }
                .padding(.bottom, 16)
            }
        }
    }
}

private struct BurstActionRow: View {
    let canCapture: Bool
    let frameCount: Int
    let onTap: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            Text("Frames captured: \(frameCount) / 60")
                .font(.caption.weight(.medium))
                .foregroundStyle(.white.opacity(0.85))
            Button(action: onTap) {
                ZStack {
                    Circle()
                        .stroke(.white.opacity(0.95), lineWidth: 4)
                        .frame(width: 76, height: 76)
                    Circle()
                        .fill(canCapture ? Color.red : Color.white.opacity(0.4))
                        .frame(width: 60, height: 60)
                }
            }
            .disabled(!canCapture)
            .accessibilityLabel("Capture")
        }
    }
}

// MARK: – Guidance panel

struct GuidancePanel: View {
    @ObservedObject var arkit: ARKitCapture

    var body: some View {
        HStack(spacing: 10) {
            DistanceTile(distanceMm: arkit.distanceMm)
            LevelTile(pitchDeg: arkit.pitchDeg)
            MotionTile(score: arkit.motionScore)
            FiducialTile(detected: arkit.fiducialDetected)
            TrackingTile(state: arkit.trackingState)
        }
        .padding(.horizontal, 12)
    }
}

private struct DistanceTile: View {
    let distanceMm: Float?
    var inWindow: Bool { (distanceMm.map { $0 >= 200 && $0 <= 400 }) ?? false }
    var body: some View {
        Tile(
            symbol: "ruler",
            label: distanceMm.map { String(format: "%.0f mm", $0) } ?? "—",
            sub: "30 cm",
            tone: inWindow ? .green : .yellow
        )
    }
}

private struct LevelTile: View {
    let pitchDeg: Float
    var aligned: Bool { abs(pitchDeg - 90) <= 15 }
    var body: some View {
        Tile(
            symbol: "level",
            label: String(format: "%.0f°", pitchDeg),
            sub: "parallel",
            tone: aligned ? .green : .yellow
        )
    }
}

private struct MotionTile: View {
    let score: Float
    var body: some View {
        Tile(
            symbol: "hand.raised.fill",
            label: score >= 0.7 ? "steady" : score >= 0.4 ? "slow down" : "moving",
            sub: nil,
            tone: score >= 0.7 ? .green : score >= 0.4 ? .yellow : .red
        )
    }
}

private struct FiducialTile: View {
    let detected: Bool
    var body: some View {
        Tile(
            symbol: detected ? "checkmark.square.fill" : "square.dashed",
            label: detected ? "fiducial" : "place sticker",
            sub: nil,
            tone: detected ? .green : .yellow
        )
    }
}

private struct TrackingTile: View {
    let state: ARCamera.TrackingState
    var body: some View {
        Tile(
            symbol: "scope",
            label: trackingLabel(state),
            sub: nil,
            tone: isTrackingNormal(state) ? .green : .yellow
        )
    }
}

private struct Tile: View {
    let symbol: String
    let label: String
    let sub: String?
    let tone: Color

    var body: some View {
        VStack(spacing: 2) {
            Image(systemName: symbol)
                .foregroundStyle(tone)
                .font(.callout)
            Text(label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.white)
            if let sub {
                Text(sub)
                    .font(.system(size: 9))
                    .foregroundStyle(.white.opacity(0.55))
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 10))
    }
}

private struct Reticle: View {
    let active: Bool
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14)
                .strokeBorder(active ? Color.green : Color.white.opacity(0.7), lineWidth: 2)
                .frame(width: 240, height: 240)
            Circle()
                .strokeBorder(active ? Color.green : Color.white.opacity(0.6), lineWidth: 1)
                .frame(width: 8, height: 8)
        }
        .allowsHitTesting(false)
    }
}

private func trackingLabel(_ s: ARCamera.TrackingState) -> String {
    switch s {
    case .normal: return "tracking"
    case .limited(.initializing): return "init"
    case .limited(.relocalizing): return "relocate"
    case .limited(.insufficientFeatures): return "low texture"
    case .limited(.excessiveMotion): return "too fast"
    case .limited: return "limited"
    case .notAvailable: return "no track"
    }
}

private func isTrackingNormal(_ s: ARCamera.TrackingState) -> Bool {
    if case .normal = s { return true }
    return false
}

// MARK: – Probe entry

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

// MARK: – Boundary

struct BoundaryAnnotationView: View {
    let onComplete: (BoundaryRecord) -> Void
    @State private var vertices: [[Double]] = []

    var body: some View {
        VStack {
            Text("Boundary annotation").font(.title2).bold()
            Text("ML proposes the wound boundary. Edit vertices as needed.")
                .font(.callout)
                .foregroundStyle(.secondary)

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

// MARK: – Uploading

struct UploadingView: View {
    let onResult: (MeasurementResult) -> Void

    var body: some View {
        VStack {
            ProgressView()
            Text("Uploading and processing…").padding()
        }
    }
}

// MARK: – Result

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
                        Image(systemName: "cube.transparent.fill").font(.title3)
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
