"""Dialog to create an invoice/payment entry with line item allocations."""
import os
import customtkinter as ctk

import config
from models.payment import add_payment, service_total_allocated
from models.project import get_by_id, get_financials
from models.service import services_for_project
from models.client import clients_for_project
from models.settings import get_company_info
from pdf.invoice import generate_invoice
from ui.widgets import label, entry, button, section_label, show_error, show_info


class PaymentFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int, on_save=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.on_save = on_save
        self.title("Add Invoice")
        self.geometry("500x680")
        self.resizable(False, True)
        self.grab_set()
        self._alloc_entries = {}  # service_id -> CTkEntry
        self._alloc_remaining = {}  # service_id -> remaining float
        self._alloc_labels = {}  # service_id -> remaining label widget
        self._build_ui()

    def _build_ui(self):
        label(self, "Add Invoice", bold=True, size=16).pack(pady=(20, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=4)

        # Amount
        section_label(scroll, "AMOUNT ($)").pack(anchor="w", pady=(8, 2))
        self._amount = entry(scroll, placeholder="e.g. 2500.00", width=220)
        self._amount.pack(anchor="w")
        self._amount.bind("<KeyRelease>", self._update_alloc_tracker)

        # Description
        section_label(scroll, "DESCRIPTION").pack(anchor="w", pady=(10, 2))
        self._desc = entry(scroll, placeholder="Invoice description", width=400)
        self._desc.pack(anchor="w")

        # Line item allocations
        section_label(scroll, "LINE ITEM ALLOCATIONS").pack(anchor="w", pady=(14, 2))
        label(
            scroll,
            "Specify how much of this payment applies to each line item.\n"
            "Total allocated must equal the payment amount.",
            size=11, fg="gray",
        ).pack(anchor="w", pady=(0, 6))

        visible_services = [
            s for s in services_for_project(self.project_db_id) if not s.is_hidden
        ]

        if not visible_services:
            label(scroll, "No visible line items available.", size=11, fg="gray").pack(anchor="w")
        else:
            for svc in visible_services:
                remaining = svc.amount - service_total_allocated(svc.id)
                self._alloc_remaining[svc.id] = remaining
                self._build_alloc_row(scroll, svc, remaining)

        # Running total tracker
        tracker_frame = ctk.CTkFrame(scroll, fg_color=("gray90", "gray20"), corner_radius=8)
        tracker_frame.pack(fill="x", pady=(10, 4))
        tracker_inner = ctk.CTkFrame(tracker_frame, fg_color="transparent")
        tracker_inner.pack(fill="x", padx=12, pady=8)
        label(tracker_inner, "Allocated:", size=12).pack(side="left")
        self._tracker_label = ctk.CTkLabel(
            tracker_inner, text="$0.00 / $0.00",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self._tracker_label.pack(side="left", padx=(6, 0))
        self._tracker_status = ctk.CTkLabel(
            tracker_inner, text="",
            font=ctk.CTkFont(size=11),
        )
        self._tracker_status.pack(side="left", padx=(10, 0))

        # Invoice description / note
        section_label(scroll, "INVOICE GENERAL DESCRIPTION (optional)").pack(anchor="w", pady=(12, 2))
        self._inv_desc = ctk.CTkTextbox(scroll, width=420, height=60, corner_radius=8)
        self._inv_desc.pack(anchor="w")

        section_label(scroll, "INVOICE NOTE (optional)").pack(anchor="w", pady=(10, 2))
        self._inv_note = ctk.CTkTextbox(scroll, width=420, height=60, corner_radius=8)
        self._inv_note.pack(anchor="w")

        button(scroll, "Save & Generate Invoice", self._save, width=220,
               fg_color="#4caf50", hover_color="#2e7d32").pack(pady=16)

    def _build_alloc_row(self, parent, svc, remaining: float):
        card = ctk.CTkFrame(parent, corner_radius=8, fg_color=("gray86", "gray17"))
        card.pack(fill="x", pady=3)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 2))

        svc_label = svc.description
        if svc.type == "order_change":
            svc_label += "  [Change Order]"
        label(top_row, svc_label, size=12, bold=True).pack(side="left", anchor="w")
        label(top_row, f"Total: ${svc.amount:,.2f}", size=11, fg="gray").pack(side="right")

        bottom_row = ctk.CTkFrame(card, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=(2, 8))

        remaining_lbl = ctk.CTkLabel(
            bottom_row,
            text=f"Remaining: ${remaining:,.2f}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        remaining_lbl.pack(side="left", anchor="w")
        self._alloc_labels[svc.id] = remaining_lbl

        alloc_entry = ctk.CTkEntry(bottom_row, placeholder_text="0.00", width=100)
        alloc_entry.pack(side="right")
        label(bottom_row, "Allocate $:", size=11).pack(side="right", padx=(0, 4))

        alloc_entry.bind("<KeyRelease>", self._update_alloc_tracker)
        self._alloc_entries[svc.id] = alloc_entry

    def _get_payment_amount(self) -> float | None:
        try:
            val = float(self._amount.get().strip())
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    def _get_alloc_total(self) -> float:
        total = 0.0
        for alloc_entry in self._alloc_entries.values():
            try:
                val = float(alloc_entry.get().strip() or "0")
                if val > 0:
                    total += val
            except ValueError:
                pass
        return total

    def _update_alloc_tracker(self, _event=None):
        payment_amt = self._get_payment_amount() or 0.0
        alloc_total = self._get_alloc_total()
        self._tracker_label.configure(text=f"${alloc_total:,.2f} / ${payment_amt:,.2f}")

        diff = payment_amt - alloc_total
        if payment_amt <= 0:
            self._tracker_status.configure(text="", text_color="gray")
        elif abs(diff) < 0.005:
            self._tracker_status.configure(text="✓ Balanced", text_color="#4caf50")
        elif diff > 0:
            self._tracker_status.configure(text=f"${diff:,.2f} unallocated", text_color="#fb8c00")
        else:
            self._tracker_status.configure(text=f"${abs(diff):,.2f} over", text_color="#e53935")

    def _save(self):
        amt_str = self._amount.get().strip()
        try:
            amt = float(amt_str)
            if amt <= 0:
                raise ValueError
        except ValueError:
            show_error("Invalid Amount", "Enter a positive number for the amount.")
            return

        allocations = []
        for svc_id, alloc_entry in self._alloc_entries.items():
            raw = alloc_entry.get().strip()
            if not raw or raw == "0":
                continue
            try:
                alloc_amt = float(raw)
                if alloc_amt <= 0:
                    continue
            except ValueError:
                show_error("Invalid Allocation", f"Allocation amount must be a number.")
                return
            remaining = self._alloc_remaining.get(svc_id, 0.0)
            if alloc_amt > remaining + 0.005:
                show_error(
                    "Allocation Exceeds Balance",
                    f"Allocation of ${alloc_amt:,.2f} exceeds the remaining balance of ${remaining:,.2f} for that line item.",
                )
                return
            allocations.append({"service_id": svc_id, "amount": alloc_amt})

        inv_desc = self._inv_desc.get("1.0", "end").strip()
        inv_note = self._inv_note.get("1.0", "end").strip()

        try:
            payment = add_payment(
                project_db_id=self.project_db_id,
                amount=amt,
                description=self._desc.get().strip(),
                invoice_description=inv_desc,
                invoice_note=inv_note,
                allocations=allocations,
            )
        except ValueError as e:
            show_error("Payment Error", str(e))
            return

        self._generate_invoice(payment)

        if self.on_save:
            self.on_save()
        self.destroy()

    def _generate_invoice(self, payment):
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        project = get_by_id(self.project_db_id)
        if not project or not base:
            return

        folder = os.path.join(base, project.project_id)
        os.makedirs(folder, exist_ok=True)
        filename = f"INV-{project.project_id}-{payment.id:04d}.pdf"
        path = os.path.join(folder, filename)

        clients = clients_for_project(self.project_db_id)
        financials = get_financials(self.project_db_id)
        company_info = get_company_info(project.company)
        services = services_for_project(self.project_db_id)

        try:
            generate_invoice(path, project, payment, clients, financials, company_info, services=services)
            show_info("Invoice Saved", f"Invoice saved:\n{filename}")
        except Exception as e:
            show_error("PDF Error", f"Invoice could not be generated:\n{e}")
