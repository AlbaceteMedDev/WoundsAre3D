// ResultsViewModel.swift
// AlbaceteMedDev
//
// Polls scan status, fetches results, and exposes data to ResultsView.

import Foundation
import SwiftUI

enum ResultsState {
    case polling
    case loading
    case loaded(ScanResultsResponse)
    case failed(String)
}

@MainActor
final class ResultsViewModel: ObservableObject {

    @Published private(set) var state: ResultsState = .polling
    @Published private(set) var pollAttempt: Int = 0

    private let scanId: String
    private let apiClient = ScanAPIClient()

    init(scanId: String) {
        self.scanId = scanId
    }

    // MARK: - Public

    func start() {
        Task { await pollThenFetch() }
    }

    // MARK: - Private

    private func pollThenFetch() async {
        // Poll status until COMPLETE or FAILED
        for attempt in 0..<AppConstants.Polling.maxAttempts {
            pollAttempt = attempt + 1

            do {
                let statusResponse = try await apiClient.getScanStatus(scanId: scanId)

                switch statusResponse.status {
                case .complete:
                    await fetchResults()
                    return
                case .failed:
                    state = .failed("Scan processing failed on the server.")
                    return
                case .uploading, .processing:
                    try await Task.sleep(
                        nanoseconds: UInt64(AppConstants.Polling.intervalSeconds * 1_000_000_000)
                    )
                }
            } catch {
                // Network hiccup — keep trying unless we've hit the limit
                if attempt == AppConstants.Polling.maxAttempts - 1 {
                    state = .failed(error.localizedDescription)
                    return
                }
                try? await Task.sleep(nanoseconds: UInt64(AppConstants.Polling.intervalSeconds * 1_000_000_000))
            }
        }
        state = .failed("Processing timed out. Please try again.")
    }

    private func fetchResults() async {
        state = .loading
        do {
            let results = try await apiClient.getScanResults(scanId: scanId)
            state = .loaded(results)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}
