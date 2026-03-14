"""
report/pdf_assembler.py

Produces a professional DDR report matching the UrbanRoof Main_DDR.pdf:
  - Dark hexagon-pattern cover page
  - Disclaimer page
  - Auto-built Table of Contents (live page numbers via multiBuild)
  - UrbanRoof branded header + footer on every content page
  - Section 1  : Introduction
  - Section 2  : General Information
  - Section 3  : Visual Observations (per-area observation tables)
  - Section 4  : Analysis & Suggestions
      4.1  Recommended treatments table
      4.2  Delayed action consequences
      4.3  Negative / Positive summary table
      4.4  Thermal image pairs  (visual + IR side-by-side)
      4.5  Visual references
  - Section 5  : Probable Root Causes
  - Section 6  : Severity Assessment (colour-coded table + callout)
  - Section 7  : Additional Notes
  - Section 8  : Missing / Unclear Information
  - Section 9  : Limitation and Precaution Note
"""

import os
import math

from reportlab.lib.pagesizes  import A4
from reportlab.lib.units      import cm
from reportlab.lib            import colors
from reportlab.lib.styles     import ParagraphStyle
from reportlab.lib.enums      import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus       import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak, KeepTogether,
    NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Colours  (from Main_DDR.pdf palette)
# ---------------------------------------------------------------------------
C_DARK     = colors.HexColor("#1C1C1C")
C_YELLOW   = colors.HexColor("#F5A623")
C_GREEN    = colors.HexColor("#4CAF50")
C_HDR_BG   = colors.HexColor("#1a1a2e")
C_WHITE    = colors.white
C_LIGHT_BG = colors.HexColor("#F5F5F5")
C_BORDER   = colors.HexColor("#CCCCCC")
C_GOOD     = colors.HexColor("#27AE60")
C_MODERATE = colors.HexColor("#E67E22")
C_POOR     = colors.HexColor("#C0392B")

SEV_COLORS = {
    "Critical": colors.HexColor("#C0392B"),
    "High":     colors.HexColor("#E67E22"),
    "Medium":   colors.HexColor("#D4AC0D"),
    "Low":      colors.HexColor("#27AE60"),
}
PRI_COLORS = {
    "Immediate":  colors.HexColor("#C0392B"),
    "Short-term": colors.HexColor("#E67E22"),
    "Long-term":  colors.HexColor("#27AE60"),
}

# ---------------------------------------------------------------------------
# Page geometry
# ---------------------------------------------------------------------------
PW, PH   = A4
MARGIN   = 1.8 * cm
DOC_W    = PW - 2 * MARGIN
FOOTER_H = 1.2 * cm
HDR_H    = 1.3 * cm


# ===========================================================================
# Styles
# ===========================================================================
def _styles():
    return {
        # cover
        "cover_label": ParagraphStyle("cover_label",
            fontName="Helvetica-Bold", fontSize=10, textColor=C_YELLOW),
        "cover_value": ParagraphStyle("cover_value",
            fontName="Helvetica", fontSize=10, textColor=C_WHITE),
        # document
        "disclaimer": ParagraphStyle("disclaimer",
            fontName="Helvetica-Oblique", fontSize=9, textColor=C_DARK,
            leading=14, alignment=TA_JUSTIFY, spaceAfter=7),
        "toc1": ParagraphStyle("toc1",
            fontName="Helvetica-Bold", fontSize=11, textColor=C_DARK,
            leading=16, spaceAfter=3),
        "toc2": ParagraphStyle("toc2",
            fontName="Helvetica", fontSize=10, textColor=C_DARK,
            leading=14, leftIndent=18, spaceAfter=2),
        "sec_title": ParagraphStyle("sec_title",
            fontName="Helvetica-Bold", fontSize=13, textColor=C_WHITE,
            leading=17),
        "area_h": ParagraphStyle("area_h",
            fontName="Helvetica-Bold", fontSize=11, textColor=C_YELLOW,
            leading=15, spaceBefore=10, spaceAfter=4),
        "sub_h": ParagraphStyle("sub_h",
            fontName="Helvetica-Bold", fontSize=10, textColor=C_DARK,
            leading=14, spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, textColor=C_DARK,
            leading=14, spaceAfter=5, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=9, textColor=C_DARK,
            leading=14, leftIndent=14, spaceAfter=3),
        "caption": ParagraphStyle("caption",
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER, spaceAfter=5),
        "img_na": ParagraphStyle("img_na",
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=colors.HexColor("#999999"), alignment=TA_CENTER),
        # table text
        "th":   ParagraphStyle("th",   fontName="Helvetica-Bold", fontSize=9,
                                textColor=C_WHITE, alignment=TA_CENTER),
        "th_l": ParagraphStyle("th_l", fontName="Helvetica-Bold", fontSize=9,
                                textColor=C_WHITE, alignment=TA_LEFT),
        "td":   ParagraphStyle("td",   fontName="Helvetica", fontSize=9,
                                textColor=C_DARK, leading=13),
        "td_c": ParagraphStyle("td_c", fontName="Helvetica", fontSize=9,
                                textColor=C_DARK, alignment=TA_CENTER),
    }


# ===========================================================================
# Canvas callbacks
# ===========================================================================
def _draw_hex_grid(c):
    sz  = 26
    col = colors.HexColor("#252525")
    w   = sz * math.sqrt(3)
    h   = sz * 2
    row = 0
    y   = -sz
    while y < PH + sz * 2:
        x = -w + (w / 2 if row % 2 else 0)
        while x < PW + w:
            pts = [
                (x + sz * math.cos(math.radians(60 * i)),
                 y + sz * math.sin(math.radians(60 * i)))
                for i in range(6)
            ]
            p = c.beginPath()
            p.moveTo(*pts[0])
            for px, py in pts[1:]:
                p.lineTo(px, py)
            p.close()
            c.setFillColor(col)
            c.setStrokeColor(col)
            c.drawPath(p, fill=1, stroke=0)
            x += w
        y   += h * 0.75
        row += 1


def _on_cover(c, doc):
    c.saveState()

    # background
    c.setFillColor(C_DARK)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)
    _draw_hex_grid(c)

    # yellow accent triangle bottom-right
    c.setFillColor(C_YELLOW)
    p = c.beginPath()
    p.moveTo(PW * 0.52, 0)
    p.lineTo(PW, 0)
    p.lineTo(PW, PH * 0.30)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # UrbanRoof wordmark
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(C_WHITE)
    c.drawRightString(PW - MARGIN, PH - 2.2 * cm, "UrbanRoof")
    c.setFont("Helvetica", 9)
    c.setFillColor(C_YELLOW)
    c.drawRightString(PW - MARGIN, PH - 2.9 * cm, "www.urbanroof.in")

    # main title
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(C_WHITE)
    c.drawCentredString(PW / 2, PH * 0.62, "Detailed Diagnosis Report")

    # green underline
    c.setStrokeColor(C_GREEN)
    c.setLineWidth(2.5)
    c.line(MARGIN * 2.5, PH * 0.595, PW - MARGIN * 2.5, PH * 0.595)

    # report id / date
    meta = doc.ddr_meta
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(C_YELLOW)
    c.drawString(MARGIN * 2, PH * 0.50, meta.get("inspection_date", ""))
    c.drawString(MARGIN * 2, PH * 0.455,
                 f"Report ID: {meta.get('report_id', 'DNR-')}")

    # prepared by / for
    lx = MARGIN * 2
    rx = PW / 2 + MARGIN
    by = MARGIN * 3.2

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(C_YELLOW)
    c.drawString(lx, by + 1.3 * cm, "Inspected & Prepared By:")
    c.drawString(rx, by + 1.3 * cm, "Prepared For:")

    c.setFont("Helvetica", 10)
    c.setFillColor(C_WHITE)
    c.drawString(lx, by + 0.6 * cm, meta.get("inspector", "Not Available"))

    addr = meta.get("address", "Not Available")
    if len(addr) > 45:
        mid   = addr.rfind(",", 0, 45) + 1
        line1 = addr[:mid].strip()
        line2 = addr[mid:].strip()
        c.drawString(rx, by + 0.6 * cm, line1)
        c.drawString(rx, by,            line2)
    else:
        c.drawString(rx, by + 0.6 * cm, addr)

    c.restoreState()


def _on_content(c, doc):
    c.saveState()

    # header bar
    c.setFillColor(C_HDR_BG)
    c.rect(0, PH - HDR_H, PW, HDR_H, fill=1, stroke=0)
    c.setFillColor(C_GREEN)
    c.rect(0, PH - HDR_H - 2, PW, 2, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_WHITE)
    c.drawString(MARGIN, PH - HDR_H + 0.38 * cm, "Detailed Diagnosis Report")

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#BBBBBB"))
    c.drawRightString(PW - MARGIN, PH - HDR_H + 0.38 * cm,
                      doc.ddr_meta.get("address", "")[:70])

    # footer
    c.setStrokeColor(C_GREEN)
    c.setLineWidth(0.8)
    c.line(MARGIN, FOOTER_H + 3, PW - MARGIN, FOOTER_H + 3)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawString(MARGIN, FOOTER_H * 0.45, "www.urbanroof.in")

    c.setFont("Helvetica-BoldOblique", 8)
    c.setFillColor(C_YELLOW)
    c.drawCentredString(PW / 2, FOOTER_H * 0.45, "UrbanRoof Private Limited")

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawRightString(PW - MARGIN, FOOTER_H * 0.45, f"Page {doc.page}")

    c.restoreState()


# ===========================================================================
# Custom DocTemplate
# ===========================================================================
class DDRDoc(BaseDocTemplate):
    def __init__(self, filename, ddr_meta, **kw):
        self.ddr_meta = ddr_meta
        super().__init__(filename, **kw)

    def afterFlowable(self, flowable):
        """Register headings so the TOC captures them."""
        if isinstance(flowable, Paragraph):
            sname = flowable.style.name
            text  = flowable.getPlainText()
            if sname == "sec_title":
                self.notify("TOCEntry", (0, text, self.page))
            elif sname == "area_h":
                self.notify("TOCEntry", (1, text, self.page))


# ===========================================================================
# Reusable flowable builders
# ===========================================================================
def _sec_hdr(title: str, s: dict, w: float) -> list:
    """Dark header bar + green rule — opens every section."""
    tbl = Table([[Paragraph(title, s["sec_title"])]], colWidths=[w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_HDR_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return [tbl, HRFlowable(width=w, thickness=2, color=C_GREEN, spaceAfter=10)]


def _kv(rows: list, s: dict, w: float) -> Table:
    """Two-column key / value info table."""
    data = [
        [Paragraph(f"<b>{k}</b>", s["td"]),
         Paragraph(str(v or "Not Available"), s["td"])]
        for k, v in rows
    ]
    tbl = Table(data, colWidths=[w * 0.36, w * 0.64])
    tbl.setStyle(TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_WHITE, C_LIGHT_BG]),
    ]))
    return tbl


def _obs_tbl(obs: dict, s: dict, w: float) -> Table:
    """Per-area observation table with aspect / finding rows."""
    def cell(text):
        return Paragraph(str(text or "Not Available"), s["td"])

    rows = [
        [Paragraph("Aspect", s["th"]),
         Paragraph("Finding", s["th_l"])],
        [cell("Visual Observation"),
         cell(obs.get("negative_observation", ""))],
        [cell("Source / Positive Side"),
         cell(obs.get("positive_observation", ""))],
        [cell("Thermal Finding"),
         cell(obs.get("thermal_finding", "Not Available"))],
        [cell("Combined Interpretation"),
         cell(obs.get("combined_interpretation", ""))],
    ]
    for conflict in (obs.get("conflicts") or []):
        rows.append([cell("Conflict Noted"), cell(conflict)])

    tbl = Table(rows, colWidths=[w * 0.26, w * 0.74])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_HDR_BG),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_BG]),
        ("FONTNAME",       (0, 1), (0, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",      (0, 1), (0, -1),  colors.HexColor("#555555")),
    ]))
    return tbl


def _img_block(path, caption: str, s: dict, iw: float, ih: float) -> list:
    """Single image or grey placeholder + caption."""
    if path and os.path.exists(path):
        try:
            return [Image(path, width=iw, height=ih),
                    Paragraph(caption, s["caption"])]
        except Exception:
            pass
    box = Table(
        [[Paragraph("Image Not Available", s["img_na"])]],
        colWidths=[iw], rowHeights=[ih]
    )
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT_BG),
        ("GRID",       (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [box, Paragraph(caption, s["caption"])]


def _img_pair(vis_path, thm_path,
              vis_cap: str, thm_cap: str,
              s: dict, w: float) -> Table:
    """Side-by-side visual + thermal image pair."""
    iw  = w * 0.465
    ih  = 5.5 * cm
    gap = w - 2 * iw
    tbl = Table(
        [[_img_block(vis_path, vis_cap, s, iw, ih),
          Spacer(gap, 1),
          _img_block(thm_path, thm_cap, s, iw, ih)]],
        colWidths=[iw, gap, iw]
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    return tbl


def _summary_tbl(area_obs: list, s: dict, w: float) -> Table:
    """Negative / Positive summary table (section 4.3)."""
    data = [[Paragraph("Impacted Area  (−ve side)", s["th"]),
             Paragraph("Exposed / Source Area  (+ve side)", s["th"])]]
    for obs in area_obs:
        data.append([
            Paragraph((obs.get("negative_observation") or "")[:220], s["td"]),
            Paragraph((obs.get("positive_observation") or "")[:220], s["td"]),
        ])
    tbl = Table(data, colWidths=[w * 0.50, w * 0.50])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_HDR_BG),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#EBF5FF"), C_WHITE]),
    ]))
    return tbl


def _severity_tbl(sev_list: list, s: dict, w: float) -> Table:
    """Colour-coded severity table (section 6)."""
    data  = [[Paragraph("Area", s["th"]),
              Paragraph("Level", s["th"]),
              Paragraph("Reasoning", s["th_l"])]]
    pills = []
    for i, item in enumerate(sev_list, start=1):
        level = item.get("level", "Low")
        bg    = SEV_COLORS.get(level, C_BORDER)
        data.append([
            Paragraph(item.get("area", "").title(), s["td"]),
            Paragraph(f"<b>{level}</b>",
                      ParagraphStyle("sp", fontName="Helvetica-Bold",
                                     fontSize=9, textColor=C_WHITE,
                                     alignment=TA_CENTER)),
            Paragraph(item.get("reasoning", "Not Available"), s["td"]),
        ])
        pills.append((i, bg))

    tbl = Table(data, colWidths=[w * 0.28, w * 0.14, w * 0.58])
    sty = TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_HDR_BG),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_BG]),
    ])
    for ri, bg in pills:
        sty.add("BACKGROUND", (1, ri), (1, ri), bg)
    tbl.setStyle(sty)
    return tbl


def _recs_tbl(recs: list, s: dict, w: float) -> Table:
    """Treatments / recommendations table (section 4.1)."""
    data  = [[Paragraph("Area",      s["th"]),
              Paragraph("Treatment", s["th"]),
              Paragraph("Priority",  s["th"]),
              Paragraph("Key Steps", s["th_l"])]]
    pills = []
    for i, rec in enumerate(recs, start=1):
        pri    = rec.get("priority", "Short-term")
        pri_bg = PRI_COLORS.get(pri, C_BORDER)
        steps  = rec.get("steps") or []
        steps_html = "<br/>".join(f"• {st}" for st in steps[:7])
        data.append([
            Paragraph(rec.get("area", "").title(), s["td"]),
            Paragraph(rec.get("treatment_name", ""), s["td"]),
            Paragraph(f"<b>{pri}</b>",
                      ParagraphStyle("pp", fontName="Helvetica-Bold",
                                     fontSize=8, textColor=C_WHITE,
                                     alignment=TA_CENTER)),
            Paragraph(steps_html, s["td"]),
        ])
        pills.append((i, pri_bg))

    tbl = Table(data, colWidths=[w*0.16, w*0.20, w*0.13, w*0.51])
    sty = TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_HDR_BG),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_BG]),
    ])
    for ri, bg in pills:
        sty.add("BACKGROUND", (2, ri), (2, ri), bg)
    tbl.setStyle(sty)
    return tbl


def _overall_callout(level: str, w: float) -> Table:
    bg = SEV_COLORS.get(level, C_MODERATE)
    tbl = Table(
        [[Paragraph(
            f"Overall Property Severity: <b>{level}</b>",
            ParagraphStyle("ov", fontName="Helvetica-Bold", fontSize=12,
                           textColor=C_WHITE, alignment=TA_CENTER)
        )]],
        colWidths=[w]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return tbl


# ===========================================================================
# Image-matching helper
# ===========================================================================
def _find_images(area_name: str, images: dict):
    """Return (visual_path, thermal_path) best matching the area name."""
    words = [w for w in area_name.lower().split() if len(w) > 3]
    vis   = None
    thm   = None
    for label, path in images.items():
        lab = label.lower()
        if not any(w in lab for w in words):
            continue
        if "thermal" in lab:
            if thm is None:
                thm = path
        else:
            if vis is None:
                vis = path
    return vis, thm


# ===========================================================================
# Main public function
# ===========================================================================
def assemble_pdf(ddr: dict, images: dict, output_path: str):
    """
    Build the full professional DDR PDF.

    Parameters
    ----------
    ddr         : synthesised DDR dict from synthesis_agent
    images      : {label: local_file_path} from image_extractor
    output_path : destination path for the generated PDF
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    s    = _styles()
    meta = (ddr.get("property_info")
            or ddr.get("property_metadata")
            or {})

    # Defaults so we never crash on missing keys
    meta.setdefault("report_id",        "DNR-")
    meta.setdefault("inspection_date",  "Not Available")
    meta.setdefault("inspector",        "Not Available")
    meta.setdefault("address",          "Not Available")
    meta.setdefault("property_type",    "Not Available")
    meta.setdefault("age_years",        "Not Available")
    meta.setdefault("floors",           "Not Available")
    meta.setdefault("previous_audit",   "No")
    meta.setdefault("previous_repairs", "No")

    frame_top = PH - MARGIN - HDR_H
    frame_bot = MARGIN + FOOTER_H

    doc = DDRDoc(
        output_path,
        ddr_meta=meta,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + HDR_H,
        bottomMargin=MARGIN + FOOTER_H,
    )

    cover_frame = Frame(0, 0, PW, PH,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0,
                        id="cover")
    content_frame = Frame(
        MARGIN, frame_bot,
        DOC_W, frame_top - frame_bot,
        id="content"
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover",   frames=[cover_frame],
                     onPage=_on_cover),
        PageTemplate(id="Content", frames=[content_frame],
                     onPage=_on_content),
    ])

    story = []

    # =========================================================
    # COVER  (canvas draws everything; one blank flowable
    #         triggers the page break to Content template)
    # =========================================================
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # =========================================================
    # DISCLAIMER
    # =========================================================
    story += _sec_hdr("Data and Information Disclaimer", s, DOC_W)
    for para in [
        "This property inspection is not an exhaustive inspection of the "
        "structure, systems, or components. The inspection may not reveal all "
        "deficiencies. A health checkup helps to reduce some of the risk "
        "involved in the property/structure and premises, but it cannot "
        "eliminate these risks, nor can the inspection anticipate future events "
        "or changes in performance due to changes in use or occupancy.",

        "It is recommended that you obtain as much information as is available "
        "about this property, including any owner disclosures, previous "
        "inspection reports, engineering reports, building permits, and reports "
        "performed for relocation companies, municipal inspection departments, "
        "lenders, insurers, and appraisers.",

        "An inspection addresses only those components and conditions that are "
        "present, visible, and accessible at the time of the inspection. The "
        "inspector is not required to move furnishings or stored items.",

        "The inspection report may address issues that are code-based; however, "
        "this is NOT a code compliance inspection and does NOT verify compliance "
        "with manufacturer's installation instructions. The inspection does NOT "
        "imply insurability or warrantability of the structure or its components.",

        "The inspection of this property is subject to the limitations and "
        "conditions set out in this Report.",
    ]:
        story.append(Paragraph(para, s["disclaimer"]))
    story.append(PageBreak())

    # =========================================================
    # TABLE OF CONTENTS
    # =========================================================
    story += _sec_hdr("Table of Contents", s, DOC_W)
    toc = TableOfContents()
    toc.levelStyles  = [s["toc1"], s["toc2"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(PageBreak())

    # =========================================================
    # SECTION 1 — INTRODUCTION
    # =========================================================
    story.append(Paragraph("SECTION 1    INTRODUCTION", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    story.append(Paragraph("1.1  Background", s["area_h"]))
    story.append(Paragraph(
        f"The property located at <b>{meta['address']}</b> has been assessed "
        "for a preliminary health inspection. The property owner approached "
        "UrbanRoof to carry out an initial site investigation and submit a "
        "Health Assessment Report based on testing and visual inspection. "
        f"Site investigation was carried out on "
        f"<b>{meta['inspection_date']}</b> and this inspection report is "
        "submitted herewith.",
        s["body"]
    ))

    story.append(Paragraph("1.2  Objective of the Health Assessment", s["area_h"]))
    for obj in [
        "To facilitate detection of all possible flaws, problems and occurrences "
        "that might exist, and to analyse cause-effects.",
        "To prioritise the immediate repair and protection measures to be taken.",
        "To evaluate the accurate scope of work for design, estimate, and cost "
        "analysis for execution and treatment.",
        "Classification of recommendations and solutions based on existing flaws, "
        "precautionary measures, and their effective implementation.",
        "Tracking and record keeping during the life expectancy or warranty period.",
    ]:
        story.append(Paragraph(f"• {obj}", s["bullet"]))

    story.append(Paragraph("1.3  Scope of Work", s["area_h"]))
    story.append(Paragraph(
        "Conducting visual site inspection using necessary assessment tools "
        "including Tapping Hammer, Crack Gauge, IR Thermography, and Moisture "
        "and pH Meter. Carried out by the UrbanRoof technical team of skilled "
        "applicators on site using appropriate access equipment.",
        s["body"]
    ))
    story.append(PageBreak())

    # =========================================================
    # SECTION 2 — GENERAL INFORMATION
    # =========================================================
    story.append(Paragraph("SECTION 2    GENERAL INFORMATION", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    story.append(Paragraph("2.1  Client and Inspection Details", s["area_h"]))
    story.append(_kv([
        ("Customer Name",      meta.get("customer_name",
                                        meta.get("address", ""))),
        ("Customer Address",   meta.get("address", "")),
        ("E-Mail Address",     meta.get("email", "Not Available")),
        ("Contact No.",        meta.get("contact", "Not Available")),
        ("Case No.",           meta.get("report_id", "")),
        ("Date of Inspection", meta.get("inspection_date", "")),
        ("Inspected By",       meta.get("inspector", "")),
    ], s, DOC_W))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("2.2  Description of Site", s["area_h"]))
    story.append(_kv([
        ("Site Address",             meta.get("address", "")),
        ("Type of Structure",        meta.get("property_type", "")),
        ("Floors",                   meta.get("floors", "")),
        ("Year of Construction",     meta.get("year_built", "Not Available")),
        ("Age of Building (years)",  meta.get("age_years", "")),
        ("Previous Structure Audit", meta.get("previous_audit", "No")),
        ("Previous Repairs",         meta.get("previous_repairs", "No")),
    ], s, DOC_W))
    story.append(PageBreak())

    # =========================================================
    # SECTION 3 — VISUAL OBSERVATIONS AND READINGS
    # =========================================================
    story.append(Paragraph(
        "SECTION 3    VISUAL OBSERVATIONS AND READINGS", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    story.append(Paragraph("3.1  Sources of Leakage — Summary", s["area_h"]))
    story.append(Paragraph(
        ddr.get("property_summary", "Not Available"), s["body"]))
    story.append(Spacer(1, 0.4 * cm))

    area_obs = ddr.get("area_observations", [])
    for idx, obs in enumerate(area_obs, start=2):
        area_title = obs.get("area", f"Area {idx}").title()
        level      = obs.get("severity", "Medium")
        sev_bg     = SEV_COLORS.get(level, C_BORDER)

        # area heading with inline severity badge on the right
        badge_p = Paragraph(
            f"<b>{level}</b>",
            ParagraphStyle("ib", fontName="Helvetica-Bold", fontSize=9,
                           textColor=C_WHITE, alignment=TA_CENTER)
        )
        hdr_row = [[Paragraph(f"3.{idx}  {area_title}", s["area_h"]), badge_p]]
        hdr_tbl = Table(hdr_row, colWidths=[DOC_W * 0.82, DOC_W * 0.18])
        hdr_tbl.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
            ("BACKGROUND",   (1, 0), (1, 0),   sev_bg),
        ]))

        story.append(KeepTogether([
            hdr_tbl,
            _obs_tbl(obs, s, DOC_W),
            Spacer(1, 0.35 * cm),
        ]))

    story.append(PageBreak())

    # =========================================================
    # SECTION 4 — ANALYSIS AND SUGGESTIONS
    # =========================================================
    story.append(Paragraph(
        "SECTION 4    ANALYSIS AND SUGGESTIONS", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    # 4.1 treatments
    story.append(Paragraph(
        "4.1  Actions Required and Suggested Therapies", s["area_h"]))
    recs = ddr.get("recommended_actions", [])
    if recs:
        story.append(_recs_tbl(recs, s, DOC_W))
    else:
        story.append(Paragraph("No recommendations recorded.", s["body"]))
    story.append(Spacer(1, 0.5 * cm))

    # 4.2 delayed action
    story.append(Paragraph(
        "4.2  Further Possibilities Due to Delayed Action", s["area_h"]))
    for rc in ddr.get("root_causes", []):
        if rc.get("if_delayed"):
            story.append(Paragraph(
                f"<b>{rc.get('area','').title()}:</b>  {rc['if_delayed']}",
                s["body"]
            ))
    story.append(Spacer(1, 0.5 * cm))

    # 4.3 summary table
    story.append(Paragraph("4.3  Summary Table", s["area_h"]))
    story.append(_summary_tbl(area_obs, s, DOC_W))
    story.append(PageBreak())

    # 4.4 thermal image pairs
    story.append(Paragraph(
        "4.4  Thermal References for Negative Side Inputs", s["area_h"]))
    for i, obs in enumerate(area_obs):
        area_name  = obs.get("area", "")
        area_title = area_name.title()
        vis, thm   = _find_images(area_name, images)
        neg_cap    = (obs.get("negative_observation") or "")[:90]

        story.append(KeepTogether([
            Paragraph(f"4.4.{i+1}  {area_title}", s["sub_h"]),
            Paragraph(f"IMAGE: {neg_cap}", s["caption"]),
            _img_pair(vis, thm,
                      f"Visual — {area_title}",
                      f"Thermal — {area_title}",
                      s, DOC_W),
            Spacer(1, 0.5 * cm),
        ]))

    story.append(PageBreak())

    # 4.5 visual references
    story.append(Paragraph(
        "4.5  Visual References for Positive Side Inputs", s["area_h"]))
    for i, obs in enumerate(area_obs):
        area_name  = obs.get("area", "")
        area_title = area_name.title()
        vis, _     = _find_images(area_name, images)

        story.append(KeepTogether([
            Paragraph(f"4.5.{i+1}  {area_title}", s["sub_h"]),
            Paragraph((obs.get("positive_observation") or "")[:220], s["body"]),
            _img_pair(vis, None,
                      f"Source — {area_title}", "",
                      s, DOC_W),
            Spacer(1, 0.4 * cm),
        ]))

    story.append(PageBreak())

    # =========================================================
    # SECTION 5 — PROBABLE ROOT CAUSES
    # =========================================================
    story.append(Paragraph("SECTION 5    PROBABLE ROOT CAUSES", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    for rc in ddr.get("root_causes", []):
        area = rc.get("area", "").title()
        story.append(Paragraph(area, s["area_h"]))
        story.append(Paragraph(rc.get("cause", "Not Available"), s["body"]))
        for f in (rc.get("contributing_factors") or []):
            story.append(Paragraph(f"• {f}", s["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())

    # =========================================================
    # SECTION 6 — SEVERITY ASSESSMENT
    # =========================================================
    story.append(Paragraph("SECTION 6    SEVERITY ASSESSMENT", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))

    story.append(Paragraph(
        "Severity ratings were assigned based on combined visual inspection and "
        "thermal imaging findings.  Colour key: "
        "<font color='#C0392B'><b>Critical</b></font> — immediate structural risk  |  "
        "<font color='#E67E22'><b>High</b></font> — active moisture, urgent attention  |  "
        "<font color='#B8860B'><b>Medium</b></font> — developing issue, attention within months  |  "
        "<font color='#27AE60'><b>Low</b></font> — preventive / cosmetic.",
        s["body"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    sev_list = ddr.get("severity_assessment", [])
    if sev_list:
        story.append(_severity_tbl(sev_list, s, DOC_W))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_overall_callout(ddr.get("overall_severity", "High"), DOC_W))
    story.append(PageBreak())

    # =========================================================
    # SECTION 7 — ADDITIONAL NOTES
    # =========================================================
    story.append(Paragraph("SECTION 7    ADDITIONAL NOTES", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))
    story.append(Paragraph(
        ddr.get("additional_notes", "No additional notes."), s["body"]))
    story.append(Spacer(1, 0.5 * cm))

    # =========================================================
    # SECTION 8 — MISSING / UNCLEAR INFORMATION
    # =========================================================
    story.append(Paragraph(
        "SECTION 8    MISSING OR UNCLEAR INFORMATION", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))
    missing = ddr.get("missing_information") or []
    if missing:
        for item in missing:
            story.append(Paragraph(f"• {item}", s["bullet"]))
    else:
        story.append(Paragraph(
            "No significant information gaps were identified.", s["body"]))
    story.append(PageBreak())

    # =========================================================
    # SECTION 9 — LIMITATION AND PRECAUTION NOTE
    # =========================================================
    story.append(Paragraph(
        "SECTION 9    LIMITATION AND PRECAUTION NOTE", s["sec_title"]))
    story.append(HRFlowable(width=DOC_W, thickness=2,
                             color=C_GREEN, spaceAfter=10))
    for lim in [
        "Information provided in this report is a general overview of the most "
        "obvious repairs that may be needed. It is not intended to be an "
        "exhaustive list. The ultimate decision of what to repair or replace "
        "is the client's.",

        "The inspection is not technically exhaustive. The property inspection "
        "provides the client with a basic overview of the condition of the unit.",

        "Some conditions noted, such as structural cracks and other signs of "
        "settlement, indicate a potential problem that the structure of the "
        "building, or at least part of it, is overstressed. A structure when "
        "stressed beyond its capacity may collapse without further warning. "
        "When such cracks suddenly develop or appear to widen, the findings "
        "must be reported immediately to a Registered Structural Engineer.",

        "If such work is beyond the scope of the inspection and the client is "
        "concerned about any conditions noted, the inspector strongly recommends "
        "consulting a qualified Licensed Contractor or Consulting Engineer.",

        "The Inspector's Report is an opinion of the present condition of the "
        "property based on a visual examination of readily accessible features. "
        "It does not include defects hidden behind walls, floors, ceilings, or "
        "any inaccessible areas.",

        "THIS IS NOT A CODE COMPLIANCE INSPECTION. The Inspector does not "
        "determine whether any aspect of the property complies with any past, "
        "present, or future codes, regulations, or other regulatory requirements.",
    ]:
        story.append(Paragraph(lim, s["disclaimer"]))
        story.append(Spacer(1, 0.15 * cm))

    # =========================================================
    # BUILD  (two passes so the TOC has accurate page numbers)
    # =========================================================
    doc.multiBuild(story)

    try:
        from pypdf import PdfReader
        pages = len(PdfReader(output_path).pages)
    except Exception:
        pages = "?"
    print(f"  PDF written → {output_path}  ({pages} pages)")