import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

# Brand colors
DARK = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#4a90d9")
LIGHT_GRAY = colors.HexColor("#f4f4f4")
MID_GRAY = colors.HexColor("#cccccc")
TEXT = colors.HexColor("#333333")


def get_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20,
                                textColor=DARK, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11,
                                   textColor=TEXT, spaceAfter=2),
        "section_header": ParagraphStyle("section_header", fontName="Helvetica-Bold",
                                         fontSize=11, textColor=DARK, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                               textColor=TEXT, spaceAfter=2),
        "body_bold": ParagraphStyle("body_bold", fontName="Helvetica-Bold", fontSize=10,
                                    textColor=TEXT, spaceAfter=2),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                                textColor=colors.grey, spaceAfter=1),
        "right": ParagraphStyle("right", fontName="Helvetica", fontSize=10,
                                textColor=TEXT, alignment=TA_RIGHT),
        "right_bold": ParagraphStyle("right_bold", fontName="Helvetica-Bold", fontSize=10,
                                     textColor=DARK, alignment=TA_RIGHT),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9,
                                textColor=colors.grey, spaceAfter=1, spaceBefore=6),
        "stamp": ParagraphStyle("stamp", fontName="Helvetica-Bold", fontSize=36,
                                textColor=colors.HexColor("#cc0000"), alignment=TA_CENTER),
        "note_text": ParagraphStyle("note_text", fontName="Helvetica-Oblique", fontSize=9,
                                    textColor=TEXT, spaceAfter=2),
    }
    return styles


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=6, spaceBefore=6)


def standard_table_style(header_color=None) -> TableStyle:
    hc = header_color or DARK
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), hc),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])


def build_header_elements(company_info: dict, doc_type: str, project_id: str, styles: dict):
    """Returns flowables for the company header block."""
    elements = []
    logo_path = os.path.join(
        ASSETS_DIR,
        "sfsb_logo.png" if "Santa Fe" in company_info["name"] else "swp_logo.png",
    )

    # Header table: logo left, company info right
    left_content = []
    if os.path.exists(logo_path):
        from reportlab.platypus import Image
        img = Image(logo_path, width=1.5 * inch, height=1.0 * inch)
        left_content = img
    else:
        left_content = Paragraph(company_info["name"], styles["title"])

    right_lines = [
        Paragraph(company_info["name"], styles["body_bold"]),
        Paragraph(company_info.get("address", ""), styles["body"]),
        Paragraph(company_info.get("phone", ""), styles["body"]),
    ]
    if company_info.get("president"):
        right_lines.insert(1, Paragraph(f"President: {company_info['president']}", styles["body"]))

    right_block = right_lines

    header_data = [[left_content, right_block]]
    header_table = Table(header_data, colWidths=[2.5 * inch, 4.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(hr())

    # Document type + Project ID
    doc_table = Table(
        [[Paragraph(doc_type, styles["title"]),
          Paragraph(f"Project ID: {project_id}", styles["right_bold"])]],
        colWidths=[4 * inch, 3 * inch],
    )
    doc_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(doc_table)
    elements.append(Spacer(1, 0.12 * inch))
    return elements


def build_client_block(clients, job_site: str, styles: dict):
    """Returns flowables for client + job site info."""
    elements = []
    elements.append(Paragraph("CLIENT INFORMATION", styles["label"]))
    for i, client in enumerate(clients):
        if len(clients) > 1:
            elements.append(Paragraph(f"Client {i+1}", styles["body_bold"]))
        if client.names:
            elements.append(Paragraph(", ".join(client.names), styles["body_bold"]))
        for email in client.emails:
            elements.append(Paragraph(email, styles["body"]))
        for phone in client.phones:
            elements.append(Paragraph(phone, styles["body"]))
        for addr in client.addresses:
            elements.append(Paragraph(addr, styles["body"]))
        if i < len(clients) - 1:
            elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("JOB SITE", styles["label"]))
    elements.append(Paragraph(job_site or "—", styles["body"]))
    return elements


def build_optional_text_blocks(description: str, note: str, styles: dict,
                               position: str = "description") -> list:
    """Build optional General Description or Note block."""
    elements = []
    if position == "description" and description:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("GENERAL DESCRIPTION", styles["label"]))
        elements.append(Paragraph(description, styles["body"]))
    if position == "note" and note:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("NOTE", styles["label"]))
        elements.append(Paragraph(note, styles["note_text"]))
    return elements


def build_totals_block(subtotal: float, tax: float, tax_rate: float,
                       total: float, styles: dict, extra_rows: list = None):
    """Returns a right-aligned totals table."""
    data = [
        ["Subtotal", f"${subtotal:,.2f}"],
        [f"Tax ({tax_rate:.1f}%)", f"${tax:,.2f}"],
    ]
    if extra_rows:
        data.extend(extra_rows)
    data.append(["TOTAL", f"${total:,.2f}"])

    t = Table(data, colWidths=[2.5 * inch, 1.5 * inch],
              hAlign="RIGHT")
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, DARK),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("TEXTCOLOR", (0, -1), (-1, -1), DARK),
    ])
    t.setStyle(style)
    return t


def footer_callback(canvas, doc):
    """Draw project ID in footer."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch, 0.5 * inch, f"Project ID: {doc.project_id}")
    canvas.drawRightString(letter[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def make_doc(path: str, project_id: str) -> SimpleDocTemplate:
    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=0.75 * inch,
    )
    doc.project_id = project_id
    return doc
