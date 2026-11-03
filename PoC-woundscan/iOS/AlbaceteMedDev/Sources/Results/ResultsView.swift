// ResultsView.swift
// AlbaceteMedDev

import SwiftUI

struct ResultsView: View {

    let scanId: String
    @StateObject private var viewModel: ResultsViewModel

    init(scanId: String) {
        self.scanId = scanId
        _viewModel = StateObject(wrappedValue: ResultsViewModel(scanId: scanId))
    }

    var body: some View {
        switch viewModel.state {
        case .polling:
            pollingView
        case .loading:
            loadingView
        case .loaded(let results):
            resultsScrollView(results)
        case .failed(let message):
            errorView(message)
        }
    }

    // MARK: - States

    private var pollingView: some View {
        VStack(spacing: 20) {
            ProgressView().progressViewStyle(.circular).scaleEffect(1.4)
            Text("Processing scan…").font(.headline)
            Text("Attempt \(viewModel.pollAttempt) of \(AppConstants.Polling.maxAttempts)")
                .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Scan Results")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { viewModel.start() }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView().progressViewStyle(.circular).scaleEffect(1.4)
            Text("Loading results…").font(.headline)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Scan Results")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { viewModel.start() }
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48)).foregroundStyle(.orange)
            Text("Something went wrong").font(.title3.bold())
            Text(message).font(.subheadline).foregroundStyle(.secondary)
                .multilineTextAlignment(.center).padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Scan Results")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { viewModel.start() }
    }

    private func resultsScrollView(_ results: ScanResultsResponse) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {

                Text("Scan \(scanId.prefix(8))…")
                    .font(.caption).foregroundStyle(.secondary)
                    .padding(.horizontal)

                sectionHeader("Measurements")
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    MeasurementCard.length(results.measurements.lengthMm)
                    MeasurementCard.width(results.measurements.widthMm)
                    MeasurementCard.bedArea(results.measurements.bedAreaCm2)
                    MeasurementCard.depth(results.measurements.depthMm)
                }
                .padding(.horizontal)

                sectionHeader("Top View Diagram")
                AsyncSVGView(urlString: results.diagrams.diagramTop)
                    .frame(maxWidth: .infinity).frame(height: 280)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)

                sectionHeader("Cross-Section Diagram")
                AsyncImageView(urlString: results.diagrams.diagramCross)
                    .frame(maxWidth: .infinity).frame(height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)

                sectionHeader("Measurement Summary")
                Text(results.narration.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(.body).foregroundStyle(.primary).lineSpacing(4)
                    .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)

                disclaimerView

                Spacer(minLength: 32)
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 16)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Scan Results")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { viewModel.start() }
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title).font(.headline).padding(.horizontal)
    }

    private var disclaimerView: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle")
                .foregroundStyle(.secondary).font(.footnote).padding(.top, 1)
            Text("These measurements are generated from LiDAR sensor data for informational purposes only. They do not constitute a clinical assessment, medical diagnosis, or treatment recommendation.")
                .font(.footnote).foregroundStyle(.secondary).lineSpacing(3)
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .padding(.horizontal)
    }
}

// MARK: - AsyncSVGView

import WebKit

struct AsyncSVGView: UIViewRepresentable {
    let urlString: String
    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.scrollView.isScrollEnabled = false
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        return webView
    }
    func updateUIView(_ webView: WKWebView, context: Context) {
        guard let url = URL(string: urlString) else { return }
        webView.load(URLRequest(url: url))
    }
}

// MARK: - AsyncImageView

struct AsyncImageView: View {
    let urlString: String
    var body: some View {
        AsyncImage(url: URL(string: urlString)) { phase in
            switch phase {
            case .empty:
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.secondarySystemGroupedBackground))
            case .success(let image):
                image.resizable().scaledToFill()
                    .frame(maxWidth: .infinity, maxHeight: .infinity).clipped()
            case .failure:
                VStack(spacing: 8) {
                    Image(systemName: "photo.badge.exclamationmark")
                        .font(.system(size: 32)).foregroundStyle(.secondary)
                    Text("Failed to load diagram").font(.caption).foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(.secondarySystemGroupedBackground))
            @unknown default:
                EmptyView()
            }
        }
    }
}

#Preview {
    NavigationStack {
        ResultsView(scanId: "6e5cb8b3-94b6-4bad-be07-8e17339f07ef")
    }
}
