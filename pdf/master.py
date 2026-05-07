import os
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.base import (
    get_styles, build_header_elements, build_client_block,
    build_optional_text_blocks, footer_callback, make_doc,
    standard_table_style, hr, DARK, MID_GRAY, LIGHT_GRAY, TEXT
)

_STATUS_LABELS = {
    "non_binding": "Non-Binding",
    "binding": "Binding",
}


def _file_uri(path: str) -> str:
    path = os.path.abspath(path).replace("\\", "/")
    if not path.startswith("/"):
        path = "/" + path
    return f"file://{path}"


def _scan_project_docs(folder: str, project_id: str) -> dict:
    """Return categorized PDF files found in the project folder."""
    docs = {"proposals": [], "change_orders": [], "quotes": [], "invoices": [], "receipts": []}
    if not os.path.isdir(folder):
        return docs
    pid = project_id.upper()
    master_name = f"MASTER-{pid}.PDF"
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".pdf"):
            continue
        fn = fname.upper()
        if fn == master_name:
            continue
        fpath = os.path.join(folder, fname)
        if fn == f"{pid}-PROPOSAL.PDF":
            docs["proposals"].append((fname, fpath))
        elif fn.startswith(f"CO-{pid}-"):
            docs["change_orders"].append((fname, fpath))
        elif fn.startswith(f"QUOTE-{pid}-"):
            docs["quotes"].append((fname, fpath))
        elif fn.startswith(f"INV-{pid}-"):
            docs["invoices"].append((fname, fpath))
        elif fn.startswith(f"REC-{pid}-"):
            docs["receipts"].append((fname, fpath))
    return docs


def generate(path: str, project, clients: list, services: list,
             payments: list, financials: dict, company_info: dict) -> None:
    """
    Generate Statement of Account PDF.

    services must include ALL services (hidden and visible) so the statement
    shows the complete picture with hidden items marked accordingly.
    payments must include all payments with allocations already loaded.
    """
    doc = make_doc(path, project.project_id)
    styles = get_styles()
    folder = os.path.dirname(path)

    subfield_style = ParagraphStyle(
        "sf", fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#666666"), leftIndent=8,
    )
    hidden_style = ParagraphStyle(
        "hi", fontName="Helvetica-Oblique", fontSize=9,
        textColor=colors.HexColor("#aaaaaa"),
    )
    alloc_style = ParagraphStyle(
        "al", fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#666666"), leftIndent=12,
    )
    footnote_style = ParagraphStyle(
        "fn", fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#888888"), spaceBefore=3,
    )
    link_style = ParagraphStyle(
        "lk", fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#1a6faf"), spaceBefore=2,
    )
    label_style = ParagraphStyle(
        "lb", fontName="Helvetica-Bold", fontSize=9,
        textColor=colors.HexColor("#555555"), spaceBefore=6, spaceAfter=2,
    )

    # Build per-service paid totals from payment allocations
    svc_paid = {}
    for pmt in payments:
        if pmt.status == "paid":
            for alloc in pmt.allocations:
                svc_paid[alloc.service_id] = svc_paid.get(alloc.service_id, 0.0) + alloc.amount

    elements = build_header_elements(
        company_info, "STATEMENT OF ACCOUNT", project.project_id, styles
    )
    elements.extend(build_client_block(clients, project.job_site, styles))

    # Project status / date info
    elements.append(Spacer(1, 0.08 * inch))
    status_text = _STATUS_LABELS.get(project.status, project.status.replace("_", " ").title())
    info_data = [["Status:", status_text, "Created:", project.created_at[:10]]]
    info_table = Table(
        info_data,
        colWidths=[0.65 * inch, 1.75 * inch, 0.65 * inch, 1.4 * inch],
        hAlign="LEFT",
    )
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#555555")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)

    elements.extend(build_optional_text_blocks(
        project.master_description, project.master_note, styles, "description"
    ))
    elements.append(Spacer(1, 0.15 * inch))

    # ─── LINE ITEMS ──────────────────────────────────────────────────────────
    elements.append(hr())
    elements.append(Paragraph("LINE ITEMS", styles["section_header"]))

    li_data = [["#", "Description", "Type", "Contract\nAmount", "Paid to\nDate", "Remaining\nBalance"]]
    li_extra = []  # (row_idx, tag) for custom styling

    for i, svc in enumerate(services):
        type_label = "Original Service" if svc.type == "original_service" else "Change Order"
        if svc.is_hidden:
            li_data.append([
                str(i + 1),
                Paragraph(svc.description or "—", hidden_style),
                Paragraph(type_label, hidden_style),
                Paragraph(f"${svc.amount:,.2f}", hidden_style),
                Paragraph("—", hidden_style),
                Paragraph("HIDDEN", hidden_style),
            ])
            li_extra.append((len(li_data) - 1, "hidden"))
        else:
            paid = svc_paid.get(svc.id, 0.0)
            li_data.append([
                str(i + 1),
                svc.description or "—",
                type_label,
                f"${svc.amount:,.2f}",
                f"${paid:,.2f}",
                f"${svc.amount - paid:,.2f}",
            ])

        for sf in svc.subfields:
            li_data.append(["", Paragraph(f"  •  {sf.text}", subfield_style), "", "", "", ""])
            li_extra.append((len(li_data) - 1, "subfield"))

    # Totals rows appended to the same table
    n_totals = len(li_data)
    li_data.append(["", "", "Subtotal", f"${financials['subtotal']:,.2f}", "", ""])
    li_data.append(["", "", f"Tax ({financials['tax_rate']:.1f}%)", f"${financials['tax']:,.2f}", "", ""])
    li_data.append([
        "", "", "PROJECT TOTAL",
        f"${financials['total']:,.2f}",
        f"${financials['paid']:,.2f}",
        f"${financials['balance']:,.2f}",
    ])

    # Column widths sum to 6.5" (letter - 2" margins)
    li_widths = [0.25 * inch, 2.35 * inch, 1.15 * inch, 1.0 * inch, 0.9 * inch, 0.85 * inch]
    li_table = Table(li_data, colWidths=li_widths)
    li_ts = standard_table_style()
    li_ts.add("ALIGN", (3, 0), (5, -1), "RIGHT")
    li_ts.add("ALIGN", (0, 0), (0, -1), "CENTER")

    for ridx, rtype in li_extra:
        if rtype == "hidden":
            li_ts.add("BACKGROUND", (0, ridx), (-1, ridx), colors.HexColor("#f5f5f5"))
        elif rtype == "subfield":
            li_ts.add("BACKGROUND", (0, ridx), (-1, ridx), colors.HexColor("#f9f9f9"))
            li_ts.add("TOPPADDING", (0, ridx), (-1, ridx), 1)
            li_ts.add("BOTTOMPADDING", (0, ridx), (-1, ridx), 1)

    # Override alternating background for totals rows
    li_ts.add("BACKGROUND", (0, n_totals), (-1, n_totals + 2), colors.white)
    li_ts.add("LINEABOVE", (2, n_totals), (-1, n_totals), 0.5, MID_GRAY)
    li_ts.add("LINEABOVE", (2, n_totals + 2), (-1, n_totals + 2), 1, DARK)
    li_ts.add("FONTNAME", (2, n_totals + 2), (5, n_totals + 2), "Helvetica-Bold")
    li_ts.add("TEXTCOLOR", (2, n_totals + 2), (5, n_totals + 2), DARK)

    li_table.setStyle(li_ts)
    elements.append(li_table)

    if any(s.is_hidden for s in services):
        elements.append(Paragraph(
            "* Hidden line items are excluded from project totals.",
            footnote_style,
        ))

    elements.append(Spacer(1, 0.15 * inch))

    # ─── PAYMENTS ────────────────────────────────────────────────────────────
    elements.append(hr())
    elements.append(Paragraph("PAYMENTS", styles["section_header"]))

    if not payments:
        elements.append(Paragraph("No payments recorded.", styles["body"]))
    else:
        svc_map = {s.id: s for s in services}
        pmt_data = [["#", "Date", "Description", "Method", "Status", "Amount"]]
        pmt_extra = []

        for i, pmt in enumerate(payments):
            status_label = "PAID" if pmt.status == "paid" else "PENDING"
            pmt_data.append([
                str(i + 1),
                pmt.created_at[:10],
                pmt.description or f"Invoice #{pmt.id}",
                pmt.payment_type or "—",
                status_label,
                f"${pmt.amount:,.2f}",
            ])
            pmt_extra.append((len(pmt_data) - 1, "paid" if pmt.status == "paid" else "unpaid"))

            for alloc in pmt.allocations:
                svc = svc_map.get(alloc.service_id)
                svc_name = svc.description if svc else f"Service #{alloc.service_id}"
                pmt_data.append([
                    "", "",
                    Paragraph(f"  └ ${alloc.amount:,.2f} → {svc_name}", alloc_style),
                    "", "", "",
                ])
                pmt_extra.append((len(pmt_data) - 1, "alloc"))

        # Payment totals rows
        n_pmt_totals = len(pmt_data)
        paid_sum = sum(p.amount for p in payments if p.status == "paid")
        pending_sum = sum(p.amount for p in payments if p.status != "paid")
        pmt_data.append(["", "", "", "", "Total Paid", f"${paid_sum:,.2f}"])
        pmt_data.append(["", "", "", "", "Total Pending", f"${pending_sum:,.2f}"])

        pmt_widths = [0.25 * inch, 0.88 * inch, 2.2 * inch, 1.12 * inch, 0.88 * inch, 1.17 * inch]
        pmt_table = Table(pmt_data, colWidths=pmt_widths)
        pmt_ts = standard_table_style()
        pmt_ts.add("ALIGN", (5, 0), (5, -1), "RIGHT")
        pmt_ts.add("ALIGN", (4, 0), (4, -1), "CENTER")
        pmt_ts.add("ALIGN", (0, 0), (0, -1), "CENTER")

        for ridx, rtype in pmt_extra:
            if rtype == "paid":
                pmt_ts.add("TEXTCOLOR", (4, ridx), (4, ridx), colors.HexColor("#2e7d32"))
                pmt_ts.add("FONTNAME", (4, ridx), (4, ridx), "Helvetica-Bold")
            elif rtype == "unpaid":
                pmt_ts.add("TEXTCOLOR", (4, ridx), (4, ridx), colors.HexColor("#e65100"))
                pmt_ts.add("FONTNAME", (4, ridx), (4, ridx), "Helvetica-Bold")
            elif rtype == "alloc":
                pmt_ts.add("BACKGROUND", (0, ridx), (-1, ridx), colors.HexColor("#f9f9f9"))
                pmt_ts.add("TOPPADDING", (0, ridx), (-1, ridx), 1)
                pmt_ts.add("BOTTOMPADDING", (0, ridx), (-1, ridx), 1)

        pmt_ts.add("BACKGROUND", (0, n_pmt_totals), (-1, n_pmt_totals + 1), colors.white)
        pmt_ts.add("LINEABOVE", (4, n_pmt_totals), (-1, n_pmt_totals), 0.5, MID_GRAY)
        pmt_ts.add("FONTNAME", (4, n_pmt_totals), (5, n_pmt_totals + 1), "Helvetica-Bold")

        pmt_table.setStyle(pmt_ts)
        elements.append(pmt_table)

    elements.append(Spacer(1, 0.15 * inch))

    # ─── FINANCIAL SUMMARY ───────────────────────────────────────────────────
    elements.append(hr())
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
        ("FONTNAME", (0, 0), (-1, 3), "Helvetica"),
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
    elements.append(Spacer(1, 0.15 * inch))

    # ─── PROJECT DOCUMENTS ───────────────────────────────────────────────────
    elements.append(hr())
    elements.append(Paragraph("PROJECT DOCUMENTS", styles["section_header"]))

    docs = _scan_project_docs(folder, project.project_id)
    any_docs = any(v for v in docs.values())

    if not any_docs:
        elements.append(Paragraph("No documents generated yet.", styles["body"]))
    else:
        doc_sections = [
            ("Proposals", docs["proposals"]),
            ("Change Orders", docs["change_orders"]),
            ("Quotes", docs["quotes"]),
            ("Invoices", docs["invoices"]),
            ("Receipts", docs["receipts"]),
        ]
        for section_title, file_list in doc_sections:
            if not file_list:
                continue
            elements.append(Paragraph(section_title, label_style))
            for fname, fpath in file_list:
                uri = _file_uri(fpath)
                elements.append(Paragraph(
                    f'  •  <link href="{uri}" color="#1a6faf">{fname}</link>',
                    link_style,
                ))

    elements.extend(build_optional_text_blocks(
        project.master_description, project.master_note, styles, "note"
    ))

    doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)
