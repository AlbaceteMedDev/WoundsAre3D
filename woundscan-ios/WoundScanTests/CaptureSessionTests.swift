import XCTest
@testable import WoundScan

final class CaptureSessionTests: XCTestCase {
    func testProbeRecordCoding() throws {
        let probe = ProbeRecord(
            xMm: 1.0, yMm: 2.0, depthMm: 5.5,
            forceCategory: .firm, probeType: .kundinGauge,
            autoDetected: true, notes: ""
        )
        let data = try JSONEncoder.iso.encode(probe)
        let str = String(data: data, encoding: .utf8) ?? ""
        XCTAssertTrue(str.contains("firm"))
        XCTAssertTrue(str.contains("kundin_gauge"))
    }

    func testBoundaryRecordEncodes() throws {
        let b = BoundaryRecord(verticesMm: [[0, 0], [10, 0], [10, 10], [0, 10]])
        let data = try JSONEncoder.iso.encode(b)
        XCTAssertGreaterThan(data.count, 0)
    }

    func testCameraIntrinsicsRoundTrip() throws {
        let intr = CameraIntrinsicsRecord(fx: 100, fy: 100, cx: 50, cy: 50, width: 100, height: 100)
        let data = try JSONEncoder.iso.encode(intr)
        let decoded = try JSONDecoder.iso.decode(CameraIntrinsicsRecord.self, from: data)
        XCTAssertEqual(decoded, intr)
    }
}
