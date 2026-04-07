from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
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

    data = [["Date", "Type", "Description", "Amount", "Running Balance"]]
    running = 0.0

    # Combine services and payments chronologically
    events = []
    for svc in services:
        label = "Original Service" if svc.type == "original_service" else "Change Order"
        events.append((svc.created_at, label, svc.description, svc.amount, True))
    for pmt in payments:
        label = f"Payment ({pmt.payment_type})"
        events.append((pmt.created_at, label, pmt.description, pmt.amount, False))

    events.sort(key=lambda e: e[0])

    subtotal = sum(s.amount for s in services)
    tax_amount = subtotal * (project.tax_rate / 100)
    project_total = subtotal + tax_amount
    paid_total = sum(p.amount for p in payments if p.status == "paid")

    # Build rows
    balance = 0.0
    billed = 0.0
    collected = 0.0
    for date, etype, desc, amt, is_charge in events:
        if is_charge:
            billed += amt
            balance = billed - collected
            data.append([date[:10], etype, desc or "—", f"+${amt:,.2f}", f"${balance:,.2f}"])
        else:
            collected += amt
            balance = billed - collected
            data.append([date[:10], etype, desc or "—", f"-${amt:,.2f}", f"${balance:,.2f}"])

    col_widths = [1.0 * inch, 1.5 * inch, 2.5 * inch, 1.1 * inch, 1.1 * inch]
    table = Table(data, colWidths=col_widths)
    ts = standard_table_style()
    ts.add("ALIGN", (3, 0), (4, -1), "RIGHT")
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
