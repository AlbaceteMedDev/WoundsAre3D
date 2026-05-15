"""Golden tests for output/pdf_report.

Renders a full ReportData fixture (including the graft and photo branches)
and asserts structural properties via pypdf. The trajectory_plot path is
deferred to its own test module — coverage instrumentation races with
matplotlib's lazy submodule init on this engine's pinned numpy/matplotlib
combo, and needs a separate fix.
"""

from __future__ import annotations

import io

from PIL import Image

from woundscan.output.pdf_report import ReportData, build_pdf_report


def _png_thumbnail(size: int = 64, color: tuple[int, int, int] = (200, 100, 80)) -> bytes:
    img = Image.new("RGB", (size, size), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _report_data(
    *,
    grafts: list[dict] | None = None,
    photo: bytes | None = None,
) -> ReportData:
    return ReportData(
        measurement_id="m-001",
        patient_token="p-deidentified",
        wound_id="w-1",
        captured_at="2026-05-15T10:00:00Z",
        clinician_id="c-42",
        volume_cm3=4.32,
        volume_ci_low=4.10,
        volume_ci_high=4.55,
        surface_area_cm2=11.20,
        surface_area_ci_low=10.80,
        surface_area_ci_high=11.55,
        max_depth_cm=0.75,
        mean_depth_cm=0.38,
        quality_grade="A",
        quality_components={"focus": 0.92, "lighting": 0.88, "coverage": 0.95},
        graft_recommendations=grafts or [],
        methodology_notes="Synthetic test fixture.",
        provenance_json='{"engine_version":"1.0.0","git_sha":"abc"}',
        photo_thumbnail_png=photo,
    )


class TestPdfReport:
    def test_baseline_renders_valid_pdf(self):
        pdf = build_pdf_report(_report_data())
        assert pdf[:5] == b"%PDF-"

    def test_page_count_at_least_one(self):
        from pypdf import PdfReader

        pdf = build_pdf_report(_report_data())
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) >= 1

    def test_graft_section_renders(self):
        from pypdf import PdfReader

        grafts = [
            {
                "product_name": "AlbacetMatrix-A",
                "overlap_delta_cm": 0.5,
                "required_cm2": 12.0,
                "selected_size_cm2": 16.0,
            },
            {
                "product_name": "AlbacetMatrix-B",
                "overlap_delta_cm": 0.3,
                "required_cm2": 12.0,
                "selected_size_cm2": 14.0,
            },
        ]
        pdf = build_pdf_report(_report_data(grafts=grafts))
        text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
        assert "Graft Recommendations" in text
        assert "AlbacetMatrix-A" in text
        assert "AlbacetMatrix-B" in text

    def test_photo_thumbnail_branch_does_not_crash(self):
        pdf = build_pdf_report(_report_data(photo=_png_thumbnail()))
        assert pdf[:5] == b"%PDF-"

    def test_photo_thumbnail_corrupt_bytes_swallowed(self):
        # The thumbnail branch is wrapped in try/except to defend against
        # corrupt blobs from older measurements — assert it stays graceful.
        pdf = build_pdf_report(_report_data(photo=b"not actually a png"))
        assert pdf[:5] == b"%PDF-"
