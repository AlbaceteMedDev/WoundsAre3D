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

    // MARK: - Capture guidance
    /// Live checks shown on the capture screen. Phantom tests (2026-11-24) showed LiDAR
    /// reads ~1.3x too far at 15 cm, inflating every length; the distance window below is
    /// PROVISIONAL until the 15 / 25 / 35 cm test on a matte surface sets it.
    enum Guidance {
        /// Acceptable camera-to-wound distance (metres, LiDAR depth at the screen centre).
        static let minDistanceM: Float = 0.25
        static let maxDistanceM: Float = 0.40

        /// Max angle between the camera axis and straight down (degrees).
        static let maxTiltDegrees: Float = 20

        /// Max camera motion while "steady" (metres/second and degrees/second).
        static let maxSpeedMetersPerSecond: Float = 0.03
        static let maxAngularSpeedDegreesPerSecond: Float = 10

        /// ARKit ambient intensity (lumens; ~1000 = well lit). Below this we warn.
        static let minAmbientIntensity: Float = 300

        /// Guidance refresh rate on screen (Hz).
        static let updateHz: Double = 10

        /// When false the Scan button stays enabled outside the window (warning only), so the
        /// distance test can still capture at 15 cm. Set true once the window is confirmed.
        static let enforce = false
    }

    // MARK: - Polling
    enum Polling {
        /// How often to poll the status endpoint (seconds)
        static let intervalSeconds: Double = 3.0

        /// Maximum number of poll attempts before giving up.
        /// 60 attempts × 3s = 3 minutes — covers SageMaker cold start (30–90s per SOW).
        static let maxAttempts = 60
    }

    // MARK: - Debug
    enum Debug {
        /// Set to a real scanId to jump directly to ResultsView without scanning.
        /// Leave nil for normal flow (required for Stage 6 acceptance runs).
        static let previewScanId: String? = nil
    }
}
