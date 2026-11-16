// CaptureView.swift
// AlbaceteMedDev

import SwiftUI
import ARKit

struct CaptureView: View {

    @StateObject private var viewModel = CaptureViewModel()
    @State private var showResults = false

    private var activeScanId: String? {
        AppConstants.Debug.previewScanId ?? viewModel.completedScanId
    }

    var body: some View {
        ZStack {
            // Camera feed — truly full screen, edge to edge
            ARViewContainer(session: viewModel.captureSession.arSession)
                .ignoresSafeArea(.all)

            // Overlay controls at the bottom
            VStack {
                Spacer()
                VStack(spacing: 12) {
                    statusPanel.padding(.horizontal, 20)
                    scanButton
                }
                .padding(.bottom, 48)
            }
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
        Button(action: { viewModel.startScan() }) {
            ZStack {
                Circle().strokeBorder(.white, lineWidth: 4).frame(width: 80, height: 80)
                Circle().fill(scanButtonFill).frame(width: 68, height: 68)
            }
        }
        .disabled(!viewModel.captureState.isActionable)
        .opacity(viewModel.captureState.isActionable ? 1.0 : 0.4)
        .accessibilityLabel("Scan")
    }

    private var scanButtonFill: Color {
        switch viewModel.captureState {
        case .scanning: return .orange
        case .uploading, .processing: return .gray
        case .failed: return .red
        default: return .white
        }
    }
}

#Preview {
    NavigationStack { CaptureView() }
}
