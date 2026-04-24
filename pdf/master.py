from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    build_optional_text_blocks, footer_callback, make_doc,
    standard_table_style, hr, DARK, MID_GRAY, LIGHT_GRAY
)


def generate(path: str, project, clients: list, services: list,
             payments: list, financials: dict, company_info: dict) -> None:
    doc = make_doc(path, project.project_id)
    styles = get_styles()

    elements = build_header_elements(company_info, "PROJECT MASTER FILE",
                                     project.project_id, styles)
    elements.extend(build_client_block(clients, project.job_site, styles))
    elements.extend(build_optional_text_blocks(
        project.master_description, project.master_note, styles, "description"
    ))
    elements.append(Spacer(1, 0.15 * inch))

    # Chronological activity table
    elements.append(Paragraph("PROJECT FINANCIAL ACTIVITY", styles["section_header"]))

    subfield_style = ParagraphStyle(
        "subfield", fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#666666"), leftIndent=8,
    )

    data = [["Date", "Type", "Description", "Amount", "Running Balance"]]

    # Combine services and payments chronologically; carry subfields with services
    events = []
    for svc in services:
        svc_label = "Original Service" if svc.type == "original_service" else "Change Order"
        events.append((svc.created_at, svc_label, svc.description, svc.amount, True,
                       getattr(svc, "subfields", [])))
    for pmt in payments:
        pmt_label = f"Payment ({pmt.payment_type})"
        events.append((pmt.created_at, pmt_label, pmt.description, pmt.amount, False, []))

    events.sort(key=lambda e: e[0])

    subtotal = sum(s.amount for s in services)
    tax_amount = subtotal * (project.tax_rate / 100)
    project_total = subtotal + tax_amount
    paid_total = sum(p.amount for p in payments if p.status == "paid")

    subfield_rows = set()
    balance = 0.0
    billed = 0.0
    collected = 0.0
    for date, etype, desc, amt, is_charge, subfields in events:
        if is_charge:
            billed += amt
            balance = billed - collected
            data.append([date[:10], etype, desc or "—", f"+${amt:,.2f}", f"${balance:,.2f}"])
        else:
            collected += amt
            balance = billed - collected
            data.append([date[:10], etype, desc or "—", f"-${amt:,.2f}", f"${balance:,.2f}"])
        for sf in subfields:
            subfield_rows.add(len(data) - 1)
            data.append(["", "", Paragraph(f"  •  {sf.text}", subfield_style), "", ""])

    col_widths = [1.0 * inch, 1.5 * inch, 2.5 * inch, 1.1 * inch, 1.1 * inch]
    table = Table(data, colWidths=col_widths)
    ts = standard_table_style()
    ts.add("ALIGN", (3, 0), (4, -1), "RIGHT")
    for r in subfield_rows:
        ts.add("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f9f9f9"))
        ts.add("TOPPADDING", (0, r), (-1, r), 1)
        ts.add("BOTTOMPADDING", (0, r), (-1, r), 1)
    table.setStyle(ts)
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))

    # Summary totals
    elements.append(Paragraph("FINANCIAL SUMMARY", styles["section_header"]))
    summary_data = [
        ["Project Subtotal", f"${financials['subtotal']:,.2f}"],
        [f"Tax ({financials['tax_rate']:.1f}%)", f"${financials['tax']:,.2f}"],
        ["Project Total", f"${financials['total']:,.2f}"],
        ["Total Paid", f"${financials['paid']:,.2f}"],
        ["Outstanding Balance", f"${financials['balance']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 1.5 * inch], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 2), "Helvetica"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.5, MID_GRAY),
        ("LINEABOVE", (0, 4), (-1, 4), 1, DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TEXTCOLOR", (0, 4), (-1, 4), DARK),
    ]))
    elements.append(summary_table)

    elements.extend(build_optional_text_blocks(
        project.master_description, project.master_note, styles, "note"
    ))

    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)
