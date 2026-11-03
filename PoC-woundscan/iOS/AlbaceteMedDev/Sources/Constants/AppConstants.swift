// AppConstants.swift
// AlbaceteMedDev
//
// Central configuration for the wound scan POC app.

import Foundation

enum AppConstants {

    // MARK: - API
    enum API {
        static let baseURL = "https://7vo1pzlg1f.execute-api.us-east-1.amazonaws.com"

        static var scansURL: URL {
            URL(string: "\(baseURL)/scans")!
        }

        static func statusURL(scanId: String) -> URL {
            URL(string: "\(baseURL)/scans/\(scanId)/status")!
        }

        static func resultsURL(scanId: String) -> URL {
            URL(string: "\(baseURL)/scans/\(scanId)/results")!
        }
    }

    // MARK: - Capture
    enum Capture {
        /// Number of LiDAR frames to capture per scan burst
        static let frameCount = 5

        /// Interval between frames in seconds (500ms)
        static let frameIntervalSeconds: Double = 0.5

        /// File types captured per frame (5 types × 5 frames = 25 files total)
        static let frameFileTypes = [
            "rgb.jpg",
            "depth.bin",
            "confidence.bin",
            "intrinsics.json",
            "metadata.json"
        ]

        /// Total files expected per scan
        static var totalFileCount: Int { frameCount * frameFileTypes.count }
    }

    // MARK: - Polling
    enum Polling {
        /// How often to poll the status endpoint (seconds)
        static let intervalSeconds: Double = 3.0

        /// Maximum number of poll attempts before giving up
        /// TODO: Restore to 60 once pipeline Lambdas are live
        static let maxAttempts = 10
    }

    // MARK: - Debug
    enum Debug {
        /// Set to a real scanId to jump directly to ResultsView without scanning
        /// Leave nil for normal flow
        static let previewScanId: String? = "6e5cb8b3-94b6-4bad-be07-8e17339f07ef"
    }
}
