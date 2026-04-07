"""Dialog to add a payment and generate its invoice PDF."""
import os
import customtkinter as ctk

import config
from models.payment import add_payment
from models.project import get_by_id, get_financials
from models.client import clients_for_project
from models.settings import get_company_info
from pdf.invoice import generate_invoice
from ui.widgets import label, entry, button, section_label, show_error, show_info


class PaymentFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int, on_save=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.on_save = on_save
        self.title("Add Payment")
        self.geometry("460x580")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        label(self, "Add Payment", bold=True, size=16).pack(pady=(20, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=4)

        section_label(scroll, "AMOUNT ($)").pack(anchor="w", pady=(8, 2))
        self._amount = entry(scroll, placeholder="e.g. 2500.00", width=220)
        self._amount.pack(anchor="w")

        section_label(scroll, "PAYMENT TYPE").pack(anchor="w", pady=(10, 2))
        self._type_var = ctk.StringVar(value="Check")
        type_menu = ctk.CTkOptionMenu(
            scroll, values=["Check", "Cash", "Wire Transfer", "Credit Card", "ACH", "Other"],
            variable=self._type_var, width=220,
        )
        type_menu.pack(anchor="w")

        section_label(scroll, "DESCRIPTION").pack(anchor="w", pady=(10, 2))
        self._desc = entry(scroll, placeholder="Payment description", width=380)
        self._desc.pack(anchor="w")

        section_label(scroll, "CHECK NUMBER (optional)").pack(anchor="w", pady=(10, 2))
        self._check_num = entry(scroll, placeholder="e.g. 1042", width=180)
        self._check_num.pack(anchor="w")

        section_label(scroll, "INVOICE GENERAL DESCRIPTION (optional)").pack(anchor="w", pady=(10, 2))
        self._inv_desc = ctk.CTkTextbox(scroll, width=380, height=60, corner_radius=8)
        self._inv_desc.pack(anchor="w")

        section_label(scroll, "INVOICE NOTE (optional)").pack(anchor="w", pady=(10, 2))
        self._inv_note = ctk.CTkTextbox(scroll, width=380, height=60, corner_radius=8)
        self._inv_note.pack(anchor="w")

        button(scroll, "Save & Generate Invoice", self._save, width=220,
               fg_color="#4caf50", hover_color="#2e7d32").pack(pady=16)

    def _save(self):
        amt_str = self._amount.get().strip()
        try:
            amt = float(amt_str)
            if amt <= 0:
                raise ValueError
        except ValueError:
            show_error("Invalid Amount", "Enter a positive number for the amount.")
            return

        inv_desc = self._inv_desc.get("1.0", "end").strip()
        inv_note = self._inv_note.get("1.0", "end").strip()

        try:
            payment = add_payment(
                project_db_id=self.project_db_id,
                amount=amt,
                payment_type=self._type_var.get(),
                description=self._desc.get().strip(),
                check_number=self._check_num.get().strip(),
                invoice_description=inv_desc,
                invoice_note=inv_note,
            )
        except ValueError as e:
            show_error("Payment Error", str(e))
            return

        # Generate invoice PDF
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

        try:
            generate_invoice(path, project, payment, clients, financials, company_info)
            show_info("Invoice Saved", f"Invoice saved:\n{filename}")
        except Exception as e:
            show_error("PDF Error", f"Invoice could not be generated:\n{e}")
