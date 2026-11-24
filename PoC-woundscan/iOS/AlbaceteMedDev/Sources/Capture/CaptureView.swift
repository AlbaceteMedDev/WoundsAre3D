// CaptureView.swift
// AlbaceteMedDev

import SwiftUI
import ARKit

struct CaptureView: View {

    @StateObject private var viewModel = CaptureViewModel()
    @State private var showResults = false
    @FocusState private var labelFocused: Bool

    private var activeScanId: String? {
        AppConstants.Debug.previewScanId ?? viewModel.completedScanId
    }

    private var guidanceColor: Color {
        if viewModel.guidance.isReady { return .green }
        return viewModel.guidance.distanceM == nil ? .white : .orange
    }

    var body: some View {
        ZStack {
            // Camera feed — truly full screen, edge to edge
            ARViewContainer(session: viewModel.captureSession.arSession)
                .ignoresSafeArea(.all)
                .onTapGesture { labelFocused = false }

            // Centre target: the backend expects the wound in the middle of the frame.
            Reticle(color: guidanceColor)
                .allowsHitTesting(false)

            VStack(spacing: 10) {
                labelField
                if viewModel.captureState.isActionable {
                    guidancePanel
                }
                Spacer()
                VStack(spacing: 12) {
                    statusPanel.padding(.horizontal, 20)
                    scanButton
                }
                .padding(.bottom, 48)
            }
            .padding(.top, 56)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .ignoresSafeArea(.all)
        .statusBarHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        .onAppear { viewModel.startSession() }
        .onDisappear { viewModel.stopSession() }
        .onChange(of: viewModel.captureState) { newState in
            if case .done = newState { showResults = true }
        }
        .onChange(of: AppConstants.Debug.previewScanId) { _ in
            if AppConstants.Debug.previewScanId != nil { showResults = true }
        }
        .fullScreenCover(isPresented: $showResults, onDismiss: { viewModel.reset() }) {
            if let scanId = activeScanId {
                ResultsView(scanId: scanId, onDismiss: { showResults = false })
            }
        }
    }

    // MARK: - Label

    private var labelField: some View {
        TextField("Label (e.g. W5 25cm matte)", text: $viewModel.label)
            .textInputAutocapitalization(.characters)
            .autocorrectionDisabled()
            .submitLabel(.done)
            .focused($labelFocused)
            .font(.subheadline)
            .foregroundStyle(.white)
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 10))
            .padding(.horizontal, 20)
            .disabled(!viewModel.captureState.isActionable)
    }

    // MARK: - Guidance

    private var guidancePanel: some View {
        let g = viewModel.guidance
        return VStack(spacing: 4) {
            HStack(spacing: 14) {
                metric("Distance", g.distanceM.map { String(format: "%.0f cm", $0 * 100) } ?? "—",
                       ok: !(g.issues.contains(.tooClose) || g.issues.contains(.tooFar) || g.issues.contains(.noDepth)))
                metric("Tilt", g.tiltDegrees.map { String(format: "%.0f°", $0) } ?? "—",
                       ok: !g.issues.contains(.tilted))
                metric("Steady", g.isSteady ? "Yes" : "No", ok: g.isSteady)
            }
            Text(g.message)
                .font(.footnote.bold())
                .foregroundStyle(g.isReady ? .green : .orange)
            if !g.isReady && !AppConstants.Guidance.enforce && g.distanceM != nil {
                Text("Test mode: scanning is still allowed")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 14)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 12))
    }

    private func metric(_ title: String, _ value: String, ok: Bool) -> some View {
        VStack(spacing: 1) {
            Text(title).font(.caption2).foregroundStyle(.white.opacity(0.7))
            Text(value).font(.subheadline.monospacedDigit().bold()).foregroundStyle(ok ? .green : .orange)
        }
    }

    // MARK: - Status

    @ViewBuilder
    private var statusPanel: some View {
        VStack(spacing: 10) {
            Text(viewModel.captureState.statusMessage)
                .font(.subheadline)
                .foregroundStyle(.white)
                .multilineTextAlignment(.center)

            if case .uploading(let progress) = viewModel.captureState {
                ProgressView(value: progress)
                    .progressViewStyle(.linear)
                    .tint(.green)
                    .animation(.easeInOut, value: progress)
            }

            if case .processing = viewModel.captureState {
                ProgressView()
                    .progressViewStyle(.circular)
                    .tint(.white)
                    .scaleEffect(1.1)
            }

            if case .failed = viewModel.captureState {
                Button("Try Again") { viewModel.reset() }
                    .font(.subheadline.bold())
                    .foregroundStyle(.white)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .background(.red.opacity(0.8), in: Capsule())
            }
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 14))
    }

    private var scanButton: some View {
        Button(action: {
            labelFocused = false
            viewModel.startScan()
        }) {
            ZStack {
                Circle().strokeBorder(.white, lineWidth: 4).frame(width: 80, height: 80)
                Circle().fill(scanButtonFill).frame(width: 68, height: 68)
            }
        }
        .disabled(!viewModel.canScan)
        .opacity(viewModel.canScan ? 1.0 : 0.4)
        .accessibilityLabel("Scan")
    }

    private var scanButtonFill: Color {
        switch viewModel.captureState {
        case .scanning: return .orange
        case .uploading, .processing: return .gray
        case .failed: return .red
        default: return viewModel.guidance.isReady ? .white : .orange.opacity(0.6)
        }
    }
}

// MARK: - Reticle

/// Circle with a crosshair at the screen centre (= image centre: the camera feed is aspect-filled).
private struct Reticle: View {
    let color: Color

    var body: some View {
        ZStack {
            Circle()
                .stroke(color, style: StrokeStyle(lineWidth: 2, dash: [8, 6]))
                .frame(width: 180, height: 180)
            Rectangle().fill(color).frame(width: 24, height: 2)
            Rectangle().fill(color).frame(width: 2, height: 24)
        }
        .shadow(color: .black.opacity(0.6), radius: 2)
    }
}

#Preview {
    NavigationStack { CaptureView() }
}
