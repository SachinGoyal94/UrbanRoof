from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os

W, H = A4

# Severity colour mapping
SEVERITY_COLORS = {
    "Critical": colors.HexColor("#C0392B"),
    "High":     colors.HexColor("#E67E22"),
    "Medium":   colors.HexColor("#F1C40F"),
    "Low":      colors.HexColor("#27AE60"),
}

PRIORITY_COLORS = {
    "Immediate":   colors.HexColor("#C0392B"),
    "Short-term":  colors.HexColor("#E67E22"),
    "Long-term":   colors.HexColor("#27AE60"),
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("title",    fontSize=20, textColor=colors.HexColor("#1a1a2e"),
                                   spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=colors.HexColor("#666666"),
                                   spaceAfter=16, alignment=TA_CENTER),
        "h1":       ParagraphStyle("h1",       fontSize=13, textColor=colors.white,
                                   backColor=colors.HexColor("#1a1a2e"),
                                   spaceBefore=14, spaceAfter=8,
                                   fontName="Helvetica-Bold",
                                   borderPadding=(6, 10, 6, 10)),
        "h2":       ParagraphStyle("h2",       fontSize=11, textColor=colors.HexColor("#1a1a2e"),
                                   spaceBefore=10, spaceAfter=4,
                                   fontName="Helvetica-Bold"),
        "body":     ParagraphStyle("body",     fontSize=9,  leading=14,
                                   textColor=colors.HexColor("#333333"), spaceAfter=5),
        "caption":  ParagraphStyle("caption",  fontSize=8,  textColor=colors.HexColor("#888888"),
                                   alignment=TA_CENTER, spaceAfter=8),
        "label":    ParagraphStyle("label",    fontSize=8,  textColor=colors.HexColor("#888888")),
    }


def _section_header(text: str, doc_width: float, style):
    tbl = Table(
        [[Paragraph(text, style)]],
        colWidths=[doc_width]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _severity_badge(level: str, styles):
    color = SEVERITY_COLORS.get(level, colors.gray)
    badge = Table([[Paragraph(
        f'<font color="white"><b>{level}</b></font>',
        ParagraphStyle("badge", fontSize=8, textColor=colors.white)
    )]], colWidths=[70])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return badge


def _embed_image(img_path: str, caption: str, doc_width: float, styles) -> list:
    elems = []
    if img_path and os.path.exists(img_path):
        try:
            img = Image(img_path, width=doc_width * 0.55, height=7 * cm)
            img.hAlign = "LEFT"
            elems.append(img)
            elems.append(Paragraph(caption, styles["caption"]))
        except Exception:
            elems.append(Paragraph(f"[Image not renderable: {caption}]", styles["caption"]))
    else:
        elems.append(Paragraph(f"Image Not Available — {caption}", styles["caption"]))
    return elems


def assemble_pdf(ddr: dict, images: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    doc_width = W - 4*cm
    s = _styles()
    story = []

    # ── Cover ────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("Detailed Diagnostic Report", s["title"]))
    meta = ddr.get("property_metadata", {})
    story.append(Paragraph(
        f"Prepared for: {meta.get('customer_name', 'Not Available')}  |  "
        f"Inspection Date: {meta.get('inspection_date', 'Not Available')}  |  "
        f"Inspector: {meta.get('inspector', 'Not Available')}",
        s["subtitle"]
    ))
    story.append(HRFlowable(width=doc_width, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.5*cm))

    # ── 1. Property Issue Summary ─────────────────────────────
    story.append(_section_header("1. Property Issue Summary", doc_width, s["h1"]))
    story.append(Paragraph(ddr.get("property_summary", "Not Available"), s["body"]))
    story.append(Spacer(1, 0.3*cm))

    # ── 2. Area-wise Observations ────────────────────────────
    story.append(_section_header("2. Area-wise Observations", doc_width, s["h1"]))
    for obs in ddr.get("area_observations", []):
        area = obs.get("area", "Unknown Area")
        story.append(Paragraph(area.title(), s["h2"]))

        rows = [
            ["Visual Observation", obs.get("visual_observation", "Not Available")],
            ["Thermal Reading",    obs.get("thermal_reading",    "Not Available")],
            ["Combined Finding",   obs.get("combined_finding",   "Not Available")],
            ["Severity",           obs.get("severity",           "Not Available")],
        ]
        conflicts = obs.get("conflicts", [])
        if conflicts:
            rows.append(["Conflicts Noted", " | ".join(conflicts)])

        tbl = Table(rows, colWidths=[3.5*cm, doc_width - 3.5*cm])
        tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",  (0, 0), (0, -1), colors.HexColor("#555555")),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#F9F9F9"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.2*cm))

        # Embed matching images for this area
        area_key = area.lower().replace(" ", "_")
        matched_imgs = {k: v for k, v in images.items() if area_key in k}
        for img_label, img_path in list(matched_imgs.items())[:2]:  # max 2 per area
            story += _embed_image(img_path, f"{area.title()} — {img_label}", doc_width, s)

        story.append(Spacer(1, 0.4*cm))

    # ── 3. Probable Root Causes ───────────────────────────────
    story.append(_section_header("3. Probable Root Causes", doc_width, s["h1"]))
    for rc in ddr.get("root_causes", []):
        story.append(Paragraph(
            f"<b>{rc.get('area', '').title()}:</b> {rc.get('cause', 'Not Available')}",
            s["body"]
        ))

    # ── 4. Severity Assessment ────────────────────────────────
    story.append(_section_header("4. Severity Assessment", doc_width, s["h1"]))
    rows = [["Area", "Severity", "Reasoning"]]
    for sv in ddr.get("severity_assessment", []):
        level = sv.get("level", "")
        color = SEVERITY_COLORS.get(level, colors.gray)
        rows.append([
            sv.get("area", "").title(),
            Paragraph(f'<font color="white"><b>{level}</b></font>',
                      ParagraphStyle("sv", fontSize=8, textColor=colors.white)),
            sv.get("reasoning", "Not Available")
        ])

    sev_tbl = Table(rows, colWidths=[4*cm, 2.5*cm, doc_width - 6.5*cm])
    sev_style = [
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]
    for i, sv in enumerate(ddr.get("severity_assessment", []), start=1):
        level = sv.get("level", "")
        bg    = SEVERITY_COLORS.get(level, colors.gray)
        sev_style.append(("BACKGROUND", (1, i), (1, i), bg))
    sev_tbl.setStyle(TableStyle(sev_style))
    story.append(sev_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── 5. Recommended Actions ───────────────────────────────
    story.append(_section_header("5. Recommended Actions", doc_width, s["h1"]))
    rows = [["Area", "Action", "Priority"]]
    for act in ddr.get("recommended_actions", []):
        rows.append([
            act.get("area", "").title(),
            act.get("action", "Not Available"),
            act.get("priority", "Not Available"),
        ])
    act_tbl = Table(rows, colWidths=[3.5*cm, doc_width - 7*cm, 3.5*cm])
    act_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(act_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── 6. Additional Notes ──────────────────────────────────
    story.append(_section_header("6. Additional Notes", doc_width, s["h1"]))
    story.append(Paragraph(ddr.get("additional_notes", "Not Available"), s["body"]))

    # ── 7. Missing / Unclear Information ─────────────────────
    story.append(_section_header("7. Missing or Unclear Information", doc_width, s["h1"]))
    missing = ddr.get("missing_information", [])
    if missing:
        for item in missing:
            story.append(Paragraph(f"• {item}", s["body"]))
    else:
        story.append(Paragraph("No missing information identified.", s["body"]))

    doc.build(story)
    print(f"  PDF written to {output_path}")