import os
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    build_optional_text_blocks, build_totals_block,
    standard_table_style, footer_callback, make_doc, hr, DARK, MID_GRAY
)


def generate(path: str, project, clients: list, services: list,
             financials: dict, company_info: dict, is_quote: bool = False) -> None:
    """Generate proposal (or quote) PDF."""
    doc = make_doc(path, project.project_id)
    styles = get_styles()

    doc_type = "QUOTE — NOT A CONTRACT" if is_quote else "PROPOSAL"
    elements = build_header_elements(company_info, doc_type, project.project_id, styles)
    elements.extend(build_client_block(clients, project.job_site, styles))

    # General Description
    desc = project.proposal_description if not is_quote else ""
    note = project.proposal_note if not is_quote else ""
    elements.extend(build_optional_text_blocks(desc, note, styles, "description"))

    elements.append(Spacer(1, 0.15 * inch))

    # Services table
    elements.append(Paragraph("SCOPE OF WORK", styles["section_header"]))
    service_data = [["#", "Description", "Amount"]]
    for i, svc in enumerate(services, 1):
        service_data.append([
            str(i),
            Paragraph(svc.description, styles["body"]),
            f"${svc.amount:,.2f}",
        ])

    svc_table = Table(service_data, colWidths=[0.4 * inch, 5.1 * inch, 1.5 * inch])
    ts = standard_table_style()
    ts.add("ALIGN", (2, 0), (2, -1), "RIGHT")
    ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
    svc_table.setStyle(ts)
    elements.append(svc_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Note
    elements.extend(build_optional_text_blocks(desc, note, styles, "note"))
    elements.append(Spacer(1, 0.1 * inch))

    # Totals
    extra = [["Down Payment Due", f"${financials['down_payment']:,.2f}"]]
    elements.append(build_totals_block(
        financials["subtotal"], financials["tax"],
        financials["tax_rate"], financials["total"],
        styles, extra_rows=extra
    ))

    if not is_quote:
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
