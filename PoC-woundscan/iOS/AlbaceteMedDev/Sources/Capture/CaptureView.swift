// CaptureView.swift
// AlbaceteMedDev

import SwiftUI
import ARKit

struct CaptureView: View {

    @StateObject private var viewModel = CaptureViewModel()
    @State private var navigateToResults = false

    private var activeScanId: String? {
        AppConstants.Debug.previewScanId ?? viewModel.completedScanId
    }

    var body: some View {
        ZStack {
            // Camera feed extends behind nav bar and home indicator
            ARViewContainer(session: viewModel.captureSession.arSession)
                .ignoresSafeArea()

            // Overlay controls at the bottom
            VStack {
                Spacer()
                VStack(spacing: 12) {
                    statusPanel.padding(.horizontal, 20)
                    scanButton
                }
                .padding(.bottom, 32)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .navigationTitle("Wound Scan")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .toolbarBackground(.black.opacity(0.6), for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbar {
            if AppConstants.Debug.previewScanId != nil {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Preview") { navigateToResults = true }
                        .foregroundStyle(.white)
                }
            }
        }
        .onAppear { viewModel.startSession() }
        .onDisappear { viewModel.stopSession() }
        .onChange(of: viewModel.captureState) { newState in
            if case .done = newState { navigateToResults = true }
        }
        .navigationDestination(isPresented: $navigateToResults) {
            if let scanId = activeScanId {
                ResultsView(scanId: scanId)
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
