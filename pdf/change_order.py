from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    standard_table_style, footer_callback, make_doc, hr, DARK, MID_GRAY
)

CO_ACCENT = colors.HexColor("#e65100")


def generate(path: str, project, clients: list, services: list, company_info: dict) -> None:
    """Generate change order PDF for order_change services."""
    doc = make_doc(path, project.project_id)
    styles = get_styles()

    elements = build_header_elements(company_info, "CHANGE ORDER", project.project_id, styles)
    elements.extend(build_client_block(clients, project.job_site, styles))
    elements.append(Spacer(1, 0.15 * inch))

    elements.append(Paragraph("CHANGE ORDER ITEMS", styles["section_header"]))
    subfield_style = ParagraphStyle(
        "subfield", fontName="Helvetica-Oblique", fontSize=9,
        textColor=colors.HexColor("#555555"), leftIndent=10, spaceAfter=1,
    )
    service_data = [["#", "Description", "Amount"]]
    subfield_rows = set()
    for i, svc in enumerate(services, 1):
        service_data.append([
            str(i),
            Paragraph(svc.description, styles["body"]),
            f"${svc.amount:,.2f}",
        ])
        for sf in getattr(svc, "subfields", []):
            subfield_rows.add(len(service_data) - 1)
            service_data.append([
                "",
                Paragraph(f"  •  {sf.text}", subfield_style),
                "",
            ])

    svc_table = Table(service_data, colWidths=[0.4 * inch, 5.1 * inch, 1.5 * inch])
    ts = standard_table_style(header_color=CO_ACCENT)
    ts.add("ALIGN", (2, 0), (2, -1), "RIGHT")
    ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
    for r in subfield_rows:
        ts.add("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f9f9f9"))
        ts.add("TOPPADDING", (0, r), (-1, r), 1)
        ts.add("BOTTOMPADDING", (0, r), (-1, r), 1)
    svc_table.setStyle(ts)
    elements.append(svc_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Totals computed from the provided change order services only
    subtotal = sum(s.amount for s in services)
    tax = subtotal * (project.tax_rate / 100)
    total = subtotal + tax

    totals_data = [
        ["Subtotal", f"${subtotal:,.2f}"],
        [f"Tax ({project.tax_rate:.1f}%)", f"${tax:,.2f}"],
        ["TOTAL", f"${total:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[2.5 * inch, 1.5 * inch], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, DARK),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("TEXTCOLOR", (0, -1), (-1, -1), DARK),
    ]))
    elements.append(totals_table)

    # Signature line
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(hr())
    sig_data = [
        [Paragraph("Client Signature", styles["small"]),
         Paragraph("Date", styles["small"])],
    ]
    sig_table = Table(sig_data, colWidths=[4 * inch, 3 * inch])
    sig_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), 0.5, colors.black),
        ("LINEABOVE", (1, 0), (1, 0), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)

    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)
