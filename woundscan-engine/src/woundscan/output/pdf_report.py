"""PDF report generation with full provenance disclosure.

Produces the clinician-facing PDF for each measurement. Sections:
- Header: patient ID (deidentified), wound ID, capture time
- Measurements: V, SA, max depth, mean depth, all with 95% CIs
- Quality: A/B/C/F grade with sub-component breakdown
- Graft sizing: per-product recommendations
- Methodology: how this was computed
- Provenance: engine version, model versions, input hashes
- Disclaimer: clinical decision support, not diagnostic
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any


@dataclass
class ReportData:
    """Payload for PDF rendering.

    Avoids tight coupling with engine internals; build this at the API
    boundary from typed engine outputs.
    """

    measurement_id: str
    patient_token: str
    wound_id: str
    captured_at: str
    clinician_id: str
    volume_cm3: float
    volume_ci_low: float
    volume_ci_high: float
    surface_area_cm2: float
    surface_area_ci_low: float
    surface_area_ci_high: float
    max_depth_cm: float
    mean_depth_cm: float
    quality_grade: str
    quality_components: dict[str, float]
    graft_recommendations: list[dict[str, Any]]
    methodology_notes: str
    provenance_json: str
    undermining: dict[str, Any] | None = None
    photo_thumbnail_png: bytes | None = None
    confidence_map_png: bytes | None = None


def build_pdf_report(data: ReportData) -> bytes:
    """Render the report. Returns the raw PDF bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image as RLImage,
    )
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        title=f"WoundScan Report {data.measurement_id}",
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(name="Mono", parent=styles["BodyText"], fontName="Courier", fontSize=8)
    )

    story = []
    story.append(Paragraph(f"WoundScan Measurement {data.measurement_id}", styles["Title"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"Patient: {data.patient_token}", styles["BodyText"]))
    story.append(Paragraph(f"Wound: {data.wound_id}", styles["BodyText"]))
    story.append(Paragraph(f"Captured: {data.captured_at}", styles["BodyText"]))
    story.append(Paragraph(f"Clinician: {data.clinician_id}", styles["BodyText"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Measurements", styles["Heading2"]))
    rows = [
        ["Quantity", "Value", "95% CI"],
        [
            "Volume (cm³)",
            f"{data.volume_cm3:.2f}",
            f"[{data.volume_ci_low:.2f}, {data.volume_ci_high:.2f}]",
        ],
        [
            "3D Surface Area (cm²)",
            f"{data.surface_area_cm2:.2f}",
            f"[{data.surface_area_ci_low:.2f}, {data.surface_area_ci_high:.2f}]",
        ],
        ["Max Depth (cm)", f"{data.max_depth_cm:.2f}", "—"],
        ["Mean Depth (cm)", f"{data.mean_depth_cm:.2f}", "—"],
    ]
    u = data.undermining
    if u and u.get("measured"):
        rows.append(
            [
                "Undermined area (cm²) †",
                f"{u['undermined_area_cm2']:.2f}",
                f"[{u['undermined_area_ci_95_low_cm2']:.2f}, "
                f"{u['undermined_area_ci_95_high_cm2']:.2f}]",
            ]
        )
        rows.append(
            [
                "Total area incl. undermining (cm²) †",
                f"{u['total_area_with_undermining_cm2']:.2f}",
                "—",
            ]
        )
        rows.append(
            [
                "Undermined volume (cm³) †",
                f"{u['undermined_volume_cm3']:.2f}",
                f"[{u['undermined_volume_ci_95_low_cm3']:.2f}, "
                f"{u['undermined_volume_ci_95_high_cm3']:.2f}]",
            ]
        )
    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(table)
    if u and u.get("measured"):
        clocks = ", ".join(f"{c:g}" for c in u.get("involved_clock_positions", []))
        story.append(Spacer(1, 0.08 * inch))
        story.append(
            Paragraph(
                "† Undermining is entered by the clinician from probe readings; it is not "
                "observed by the scanner, which cannot see beneath intact skin. Maximum extent "
                f"{u['max_extent_mm']:.1f} mm at {u['max_extent_clock_hours']:g} o'clock"
                + (f"; involved clock positions {clocks}." if clocks else ".")
                + " The undermined volume additionally assumes a pocket height of "
                f"{u['pocket_height_mm']:.1f} mm ({u['pocket_height_basis']}); the probe does "
                "not measure pocket height.",
                styles["BodyText"],
            )
        )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph(f"Quality Grade: {data.quality_grade}", styles["Heading2"]))
    qrows = [["Component", "Score"]] + [
        [k, f"{v:.2f}"] for k, v in sorted(data.quality_components.items())
    ]
    qt = Table(qrows, hAlign="LEFT")
    qt.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ]
        )
    )
    story.append(qt)
    story.append(Spacer(1, 0.15 * inch))

    if data.graft_recommendations:
        story.append(Paragraph("Graft Recommendations", styles["Heading2"]))
        for rec in data.graft_recommendations:
            story.append(
                Paragraph(
                    f"<b>{rec.get('product_name', '?')}</b> "
                    f"(overlap delta {rec.get('overlap_delta_cm', '?')} cm) — "
                    f"required {rec.get('required_cm2', 0):.2f} cm², "
                    f"select {rec.get('selected_size_cm2', '—')} cm² stock size",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 0.1 * inch))

    if data.photo_thumbnail_png is not None:
        try:
            img = RLImage(
                io.BytesIO(data.photo_thumbnail_png),
                width=3 * inch,
                height=3 * inch,
                kind="proportional",
            )
            story.append(img)
        except Exception:
            pass

    story.append(Paragraph("Methodology", styles["Heading2"]))
    story.append(Paragraph(data.methodology_notes, styles["BodyText"]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Provenance", styles["Heading2"]))
    for line in data.provenance_json.split(","):
        story.append(Paragraph(line, styles["Mono"]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            "<i>Clinical Decision Support. Not for diagnostic use. The clinician "
            "retains decision authority. Methodology provided for transparency.</i>",
            styles["BodyText"],
        )
    )

    doc.build(story)
    return buf.getvalue()
