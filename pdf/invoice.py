from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    build_optional_text_blocks, build_totals_block,
    standard_table_style, footer_callback, make_doc, hr, MID_GRAY
)


def _build_invoice_elements(project, payment, clients, financials,
                             company_info, styles, is_receipt=False):
    inv_num = f"INV-{project.project_id}-{payment.id:04d}"
    doc_type = f"{'PAID RECEIPT' if is_receipt else 'INVOICE'}  {inv_num}"
    elements = build_header_elements(company_info, doc_type, project.project_id, styles)
    elements.extend(build_client_block(clients, project.job_site, styles))

    # General Description
    elements.extend(build_optional_text_blocks(
        payment.invoice_description, payment.invoice_note, styles, "description"
    ))

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph("PAYMENT DETAILS", styles["section_header"]))

    detail_data = [
        ["Description", payment.description or "—"],
        ["Payment Type", payment.payment_type or "—"],
        ["Check #", payment.check_number or "—"],
        ["Date", payment.created_at[:10]],
        ["Amount", f"${payment.amount:,.2f}"],
    ]
    detail_table = Table(detail_data, colWidths=[2 * inch, 5 * inch])
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Note
    elements.extend(build_optional_text_blocks(
        payment.invoice_description, payment.invoice_note, styles, "note"
    ))
    elements.append(Spacer(1, 0.1 * inch))

    # Project financial summary
    elements.append(Paragraph("PROJECT SUMMARY", styles["section_header"]))
    elements.append(build_totals_block(
        financials["subtotal"], financials["tax"],
        financials["tax_rate"], financials["total"], styles
    ))

    if is_receipt:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("PAID", styles["stamp"]))

    return elements


def generate_invoice(path: str, project, payment, clients, financials,
                     company_info: dict) -> None:
    doc = make_doc(path, project.project_id)
    styles = get_styles()
    elements = _build_invoice_elements(
        project, payment, clients, financials, company_info, styles, is_receipt=False
    )
    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)


def generate_receipt(path: str, project, payment, clients, financials,
                     company_info: dict) -> None:
    doc = make_doc(path, project.project_id)
    styles = get_styles()
    elements = _build_invoice_elements(
        project, payment, clients, financials, company_info, styles, is_receipt=True
    )
    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)
