from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    build_optional_text_blocks, build_totals_block,
    standard_table_style, footer_callback, make_doc, hr, MID_GRAY
)


def _build_invoice_elements(project, payment, clients, financials,
                             company_info, styles, is_receipt=False,
                             services=None):
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

    if is_receipt:
        detail_data = [
            ["Description", payment.description or "—"],
            ["Payment Type", payment.payment_type or "—"],
            ["Payment Description", payment.payment_description or "—"],
            ["Date", payment.created_at[:10]],
            ["Amount", f"${payment.amount:,.2f}"],
        ]
    else:
        detail_data = [
            ["Description", payment.description or "—"],
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

    # Line item allocation breakdown
    if payment.allocations:
        svc_map = {s.id: s for s in (services or [])}
        elements.append(Spacer(1, 0.12 * inch))
        elements.append(Paragraph("ALLOCATION BREAKDOWN", styles["section_header"]))
        alloc_data = [["Line Item", "Amount"]]
        for alloc in payment.allocations:
            svc = svc_map.get(alloc.service_id)
            svc_name = svc.description if svc else f"Service #{alloc.service_id}"
            alloc_data.append([svc_name, f"${alloc.amount:,.2f}"])
        alloc_table = Table(alloc_data, colWidths=[5 * inch, 2 * inch])
        alloc_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ]))
        elements.append(alloc_table)

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
                     company_info: dict, services=None) -> None:
    doc = make_doc(path, project.project_id)
    styles = get_styles()
    elements = _build_invoice_elements(
        project, payment, clients, financials, company_info, styles,
        is_receipt=False, services=services,
    )
    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)


def generate_receipt(path: str, project, payment, clients, financials,
                     company_info: dict, services=None) -> None:
    doc = make_doc(path, project.project_id)
    styles = get_styles()
    elements = _build_invoice_elements(
        project, payment, clients, financials, company_info, styles,
        is_receipt=True, services=services,
    )
    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)
