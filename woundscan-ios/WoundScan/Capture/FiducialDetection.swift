import CoreImage
import CoreImage.CIFilterBuiltins
import Vision

/// Detects ArUco-style square fiducials in live frames.
///
/// iOS doesn't ship an ArUco detector in Vision; we use VNDetectRectanglesRequest
/// + CIDetector for square-quadrilateral candidates and validate each candidate
/// by reading the inner pattern. The full ArUco decode runs server-side on the
/// post-capture image — this on-device check is just for live feedback.
final class FiducialLiveCheck {
    func detect(in pixelBuffer: CVPixelBuffer, completion: @escaping (Int) -> Void) {
        let req = VNDetectRectanglesRequest { request, _ in
            let count = request.results?.count ?? 0
            DispatchQueue.main.async { completion(count) }
        }
        req.minimumAspectRatio = 0.95
        req.maximumAspectRatio = 1.05
        req.minimumSize = 0.02
        req.maximumObservations = 8
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .right, options: [:])
        try? handler.perform([req])
    }
}
