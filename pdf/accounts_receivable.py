"""Accounts Receivable Report PDF generator (cross-project, standalone)."""
from datetime import datetime

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import get_styles, hr, standard_table_style, DARK, MID_GRAY, LIGHT_GRAY

_STATUS_LABELS = {
    "non_binding": "Non-Binding",
    "binding": "Binding",
    "completed": "Completed",
}

_COMPANY_LABELS = {
    "sfsb": "Santa Fe Style Builders",
    "swp": "Southwest Plastering Co.",
}

# Column widths sum to 6.5" (letter - 2" margins)
_COL_WIDTHS = [0.85*inch, 1.80*inch, 0.80*inch, 0.70*inch, 0.85*inch, 0.75*inch, 0.75*inch]

_SUBTOTAL_BG = colors.HexColor("#e8f0fe")
_GRAND_BG = colors.HexColor("#d0e4ff")


def generate(path: str, projects_data: list) -> None:
    """
    Generate Accounts Receivable Report PDF.

    projects_data: list of dicts with keys:
        project_id (str), company (str), status (str), created_at (str),
        client_names (list[str]), financials (dict: total, paid, balance)
    """
    generated_date = datetime.now().strftime("%B %d, %Y")

    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=0.75 * inch,
    )

    styles = get_styles()
    elements = []

    # ── Report header ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("ACCOUNTS RECEIVABLE REPORT", styles["title"]),
        Paragraph(f"Generated: {generated_date}", styles["right"]),
    ]]
    header_table = Table(header_data, colWidths=[4.0 * inch, 2.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(hr())
    elements.append(Spacer(1, 0.08 * inch))

    # ── Per-company sections ─────────────────────────────────────────────────
    by_company: dict[str, list] = {}
    for p in projects_data:
        by_company.setdefault(p["company"], []).append(p)

    grand_total = grand_paid = grand_balance = 0.0

    for company_key in ["sfsb", "swp"]:
        company_projects = by_company.get(company_key, [])
        if not company_projects:
            continue

        company_name = _COMPANY_LABELS.get(company_key, company_key)
        elements.append(Paragraph(company_name.upper(), styles["section_header"]))

        headers = [
            "Project ID", "Client(s)", "Status", "Created",
            "Contract\nAmt", "Total\nPaid", "Balance\nDue",
        ]
        table_data = [headers]

        co_total = co_paid = co_balance = 0.0

        for p in company_projects:
            fin = p["financials"]
            client_str = ", ".join(p["client_names"]) if p["client_names"] else "—"
            status_label = _STATUS_LABELS.get(p["status"], p["status"].replace("_", " ").title())

            table_data.append([
                p["project_id"],
                client_str,
                status_label,
                p["created_at"][:10],
                f"${fin['total']:,.2f}",
                f"${fin['paid']:,.2f}",
                f"${fin['balance']:,.2f}",
            ])
            co_total += fin["total"]
            co_paid += fin["paid"]
            co_balance += fin["balance"]

        subtotal_row = len(table_data)
        table_data.append([
            "", "SUBTOTAL", "", "",
            f"${co_total:,.2f}",
            f"${co_paid:,.2f}",
            f"${co_balance:,.2f}",
        ])

        grand_total += co_total
        grand_paid += co_paid
        grand_balance += co_balance

        ts = standard_table_style()
        ts.add("ALIGN", (4, 0), (6, -1), "RIGHT")
        ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
        ts.add("BACKGROUND", (0, subtotal_row), (-1, subtotal_row), _SUBTOTAL_BG)
        ts.add("FONTNAME", (0, subtotal_row), (-1, subtotal_row), "Helvetica-Bold")
        ts.add("LINEABOVE", (0, subtotal_row), (-1, subtotal_row), 1, DARK)
        ts.add("TEXTCOLOR", (0, subtotal_row), (-1, subtotal_row), DARK)

        t = Table(table_data, colWidths=_COL_WIDTHS, repeatRows=1)
        t.setStyle(ts)
        elements.append(t)
        elements.append(Spacer(1, 0.18 * inch))

    # ── Grand totals ─────────────────────────────────────────────────────────
    elements.append(hr())
    elements.append(Paragraph("GRAND TOTALS", styles["section_header"]))

    grand_data = [
        ["Total Contract Value", f"${grand_total:,.2f}"],
        ["Total Paid",           f"${grand_paid:,.2f}"],
        ["Total Outstanding",    f"${grand_balance:,.2f}"],
    ]
    grand_table = Table(grand_data, colWidths=[2.5 * inch, 1.5 * inch], hAlign="RIGHT")
    grand_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, 1), "Helvetica"),
        ("FONTNAME",    (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 11),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE",   (0, 1), (-1, 1), 0.5, MID_GRAY),
        ("LINEABOVE",   (0, 2), (-1, 2), 1.0, DARK),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR",   (0, 2), (-1, 2), DARK),
        ("BACKGROUND",  (0, 2), (-1, 2), _GRAND_BG),
    ]))
    elements.append(grand_table)

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(inch, 0.5 * inch,
                          f"Accounts Receivable Report — {generated_date}")
        canvas.drawRightString(letter[0] - inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
