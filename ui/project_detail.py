"""Project detail view with Overview, Services, and Payments tabs."""
import os
import customtkinter as ctk
import tkinter.messagebox as mb

import config
from models.project import get_by_id, get_financials, set_binding, update_proposal_texts, update_master_texts, update_color
from models.client import clients_for_project
from models.service import services_for_project, delete_service
from models.payment import payments_for_project, set_paid, get_by_id as get_payment
from models.settings import get_company_info, verify_pin
from pdf.proposal import generate as generate_proposal
from pdf.invoice import generate_receipt
from pdf.master import generate as generate_master
from ui.theme import COLOR_THEMES, COMPANY_LABELS, STATUS_LABELS, STATUS_COLORS
from ui.widgets import label, button, section_label, show_error, show_info, ask_yes_no
from ui.service_form import ServiceFormDialog
from ui.payment_form import PaymentFormDialog
from ui.quote_form import QuoteFormDialog
from ui.startup import PinEntryDialog


class ProjectDetailScreen(ctk.CTkFrame):
    def __init__(self, parent, project_db_id: int, on_back, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.project_db_id = project_db_id
        self.on_back = on_back
        self._load()
        self._build_ui()

    def _load(self):
        self._project = get_by_id(self.project_db_id)
        self._clients = clients_for_project(self.project_db_id)
        self._services = services_for_project(self.project_db_id)
        self._payments = payments_for_project(self.project_db_id)
        self._financials = get_financials(self.project_db_id)

    def refresh(self):
        self._load()
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self):
        proj = self._project
        color = COLOR_THEMES.get(proj.color_theme, COLOR_THEMES["blue"])
        accent = color["hex"]

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=accent, corner_radius=0)
        header.pack(fill="x")

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=32, pady=16)

        back_btn = button(header_inner, "← Back", self.on_back, width=80,
                          fg_color="transparent", hover_color=color["dark"])
        back_btn.pack(side="left")
        back_btn.configure(text_color="white")

        ctk.CTkLabel(
            header_inner, text=proj.project_id,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=16)

        company_lbl = ctk.CTkLabel(
            header_inner,
            text=COMPANY_LABELS.get(proj.company, proj.company),
            font=ctk.CTkFont(size=11),
            text_color="white",
            fg_color=color["dark"],
            corner_radius=6, padx=8, pady=2,
        )
        company_lbl.pack(side="left")

        status_lbl = ctk.CTkLabel(
            header_inner,
            text=STATUS_LABELS.get(proj.status, proj.status),
            font=ctk.CTkFont(size=11),
            text_color="white",
            fg_color=STATUS_COLORS.get(proj.status, "#888"),
            corner_radius=6, padx=8, pady=2,
        )
        status_lbl.pack(side="left", padx=(8, 0))

        # Color picker (swatches on right)
        color_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        color_frame.pack(side="right")
        for cname, cmeta in COLOR_THEMES.items():
            sw = ctk.CTkFrame(color_frame, width=20, height=20, corner_radius=10,
                              fg_color=cmeta["hex"], cursor="hand2")
            sw.pack(side="left", padx=2)
            sw.bind("<Button-1>", lambda e, n=cname: self._change_color(n))

        # ── Action buttons ───────────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=32, pady=(12, 0))

        button(actions, "Mark as Binding", self._mark_binding, width=160,
               fg_color="#4caf50" if proj.status == "non_binding" else "gray",
               hover_color="#2e7d32").pack(side="left", padx=(0, 8))
        button(actions, "Generate Master File", self._generate_master, width=180).pack(side="left", padx=(0, 8))
        button(actions, "Generate Quote", self._open_quote, width=140,
               fg_color="#8e44ad", hover_color="#6a1f82").pack(side="left")

        # ── Tabs ─────────────────────────────────────────────────────────────
        self._tabview = ctk.CTkTabview(self, anchor="w")
        self._tabview.pack(fill="both", expand=True, padx=32, pady=12)
        self._tabview.add("Overview")
        self._tabview.add("Services")
        self._tabview.add("Payments")

        self._build_overview_tab(self._tabview.tab("Overview"))
        self._build_services_tab(self._tabview.tab("Services"))
        self._build_payments_tab(self._tabview.tab("Payments"))

    # ── Overview Tab ────────────────────────────────────────────────────────

    def _build_overview_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Client info
        section_label(scroll, "CLIENTS").pack(anchor="w", pady=(8, 4))
        for i, client in enumerate(self._clients):
            frame = ctk.CTkFrame(scroll, corner_radius=8)
            frame.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(frame, fg_color="transparent")
            inner.pack(anchor="w", padx=12, pady=8)
            if len(self._clients) > 1:
                label(inner, f"Client {i+1}", bold=True, size=12).pack(anchor="w")
            if client.names:
                label(inner, ", ".join(client.names), bold=True, size=13).pack(anchor="w")
            for email in client.emails:
                label(inner, email, size=11, fg="gray").pack(anchor="w")
            for phone in client.phones:
                label(inner, phone, size=11, fg="gray").pack(anchor="w")
            for addr in client.addresses:
                label(inner, addr, size=11, fg="gray").pack(anchor="w")

        # Job site
        section_label(scroll, "JOB SITE").pack(anchor="w", pady=(12, 4))
        ctk.CTkFrame(scroll, corner_radius=8, fg_color=("gray90", "gray20")).pack(fill="x", pady=2)
        label(scroll, self._project.job_site or "—", size=12).pack(anchor="w", padx=4)

        # Financial summary
        section_label(scroll, "FINANCIAL SUMMARY").pack(anchor="w", pady=(16, 4))
        fin = self._financials
        rows = [
            ("Subtotal",       f"${fin['subtotal']:,.2f}"),
            (f"Tax ({fin['tax_rate']:.1f}%)", f"${fin['tax']:,.2f}"),
            ("Project Total",  f"${fin['total']:,.2f}"),
            ("Down Payment",   f"${self._project.down_payment:,.2f}"),
            ("Total Paid",     f"${fin['paid']:,.2f}"),
            ("Balance Remaining", f"${fin['balance']:,.2f}"),
        ]
        for i, (lbl_text, val_text) in enumerate(rows):
            row = ctk.CTkFrame(scroll, corner_radius=6,
                               fg_color=("gray93", "gray18") if i % 2 == 0 else ("white", "gray23"))
            row.pack(fill="x", pady=1)
            label(row, lbl_text, size=12, bold=(lbl_text in ("Project Total", "Balance Remaining"))
                  ).pack(side="left", padx=12, pady=6)
            label(row, val_text, size=12, bold=(lbl_text in ("Project Total", "Balance Remaining"))
                  ).pack(side="right", padx=12, pady=6)

    # ── Services Tab ────────────────────────────────────────────────────────

    def _build_services_tab(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))
        button(top, "+ Add Service", lambda: self._open_service_form("original_service"),
               width=140, fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=(0, 8))
        button(top, "+ Add Change Order", lambda: self._open_service_form("order_change"),
               width=170, fg_color="#fb8c00", hover_color="#e65100").pack(side="left")

        # Down payment (editable)
        dp_frame = ctk.CTkFrame(tab, corner_radius=8)
        dp_frame.pack(fill="x", pady=(8, 0))
        dp_inner = ctk.CTkFrame(dp_frame, fg_color="transparent")
        dp_inner.pack(fill="x", padx=12, pady=8)
        section_label(dp_inner, "DOWN PAYMENT ($)").pack(side="left", padx=(0, 10))
        self._dp_entry = ctk.CTkEntry(dp_inner, width=130, placeholder_text="e.g. 1500")
        self._dp_entry.insert(0, str(self._project.down_payment))
        self._dp_entry.pack(side="left", padx=(0, 8))
        button(dp_inner, "Update", self._save_down_payment,
               width=80, height=28).pack(side="left")

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=4)

        originals = [s for s in self._services if s.type == "original_service"]
        changes = [s for s in self._services if s.type == "order_change"]

        if originals:
            section_label(scroll, "ORIGINAL SERVICES").pack(anchor="w", pady=(4, 2))
            for svc in originals:
                self._service_row(scroll, svc)

        if changes:
            section_label(scroll, "CHANGE ORDERS").pack(anchor="w", pady=(12, 2))
            for svc in changes:
                self._service_row(scroll, svc, accent_color="#fb8c00")

        # Totals
        fin = self._financials
        section_label(scroll, "TOTALS").pack(anchor="w", pady=(16, 4))
        for lbl_text, val_text in [
            ("Subtotal", f"${fin['subtotal']:,.2f}"),
            (f"Tax ({fin['tax_rate']:.1f}%)", f"${fin['tax']:,.2f}"),
            ("Total", f"${fin['total']:,.2f}"),
        ]:
            row = ctk.CTkFrame(scroll, corner_radius=6, fg_color=("gray93", "gray18"))
            row.pack(fill="x", pady=1)
            label(row, lbl_text, size=12).pack(side="left", padx=12, pady=5)
            label(row, val_text, size=12, bold=(lbl_text == "Total")).pack(side="right", padx=12, pady=5)

    def _service_row(self, parent, svc, accent_color="#4a90d9"):
        row = ctk.CTkFrame(parent, corner_radius=8)
        row.pack(fill="x", pady=3)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=6)
        label(inner, svc.description, size=12).pack(side="left", anchor="w")
        label(inner, f"${svc.amount:,.2f}", bold=True, size=12).pack(side="right")
        button(inner, "Delete", lambda s=svc: self._delete_service(s),
               width=70, height=24, fg_color="#e53935", hover_color="#b71c1c").pack(side="right", padx=8)

    def _delete_service(self, svc):
        if ask_yes_no("Delete Service", f"Delete '{svc.description}'?"):
            delete_service(svc.id)
            self.refresh()

    def _save_down_payment(self):
        try:
            val = float(self._dp_entry.get().strip() or "0")
        except ValueError:
            show_error("Invalid Amount", "Down payment must be a number.")
            return
        from models.project import update_down_payment
        update_down_payment(self.project_db_id, val)
        self.refresh()

    # ── Payments Tab ────────────────────────────────────────────────────────

    def _build_payments_tab(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))
        button(top, "+ Add Payment", self._open_payment_form, width=140,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="left")

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=4)

        if not self._payments:
            label(scroll, "No payments recorded.", fg="gray", size=13).pack(pady=20)
            return

        for pmt in self._payments:
            self._payment_row(scroll, pmt)

        # Balance summary
        fin = self._financials
        section_label(scroll, "BALANCE SUMMARY").pack(anchor="w", pady=(16, 4))
        for lbl_text, val_text in [
            ("Project Total", f"${fin['total']:,.2f}"),
            ("Total Paid",    f"${fin['paid']:,.2f}"),
            ("Balance",       f"${fin['balance']:,.2f}"),
        ]:
            row = ctk.CTkFrame(scroll, corner_radius=6, fg_color=("gray93", "gray18"))
            row.pack(fill="x", pady=1)
            label(row, lbl_text, size=12).pack(side="left", padx=12, pady=5)
            label(row, val_text, size=12, bold=(lbl_text == "Balance")).pack(side="right", padx=12, pady=5)

    def _payment_row(self, parent, pmt):
        status_color = "#4caf50" if pmt.status == "paid" else "#fb8c00"
        row = ctk.CTkFrame(parent, corner_radius=8)
        row.pack(fill="x", pady=3)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        # Left: description + meta
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        label(info, pmt.description or f"Payment #{pmt.id}", size=12, bold=True).pack(anchor="w")
        meta = f"{pmt.payment_type}"
        if pmt.check_number:
            meta += f"  •  Check #{pmt.check_number}"
        meta += f"  •  {pmt.created_at[:10]}"
        label(info, meta, size=11, fg="gray").pack(anchor="w")

        # Right: amount + status + mark paid
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        label(right, f"${pmt.amount:,.2f}", bold=True, size=13).pack(anchor="e")
        ctk.CTkLabel(right, text=pmt.status.upper(),
                     font=ctk.CTkFont(size=10), fg_color=status_color,
                     text_color="white", corner_radius=6, padx=6, pady=2).pack(anchor="e", pady=2)
        if pmt.status == "unpaid":
            button(right, "Mark Paid", lambda p=pmt: self._mark_paid(p),
                   width=100, height=26, fg_color="#4a90d9", hover_color="#2c6faf").pack(anchor="e", pady=2)

    # ── Actions ─────────────────────────────────────────────────────────────

    def _change_color(self, color_name: str):
        update_color(self.project_db_id, color_name)
        self.refresh()

    def _mark_binding(self):
        proj = self._project
        if proj.status == "binding":
            show_info("Already Binding", "This project is already binding.")
            return

        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if not base:
            show_error("No Output Directory", "Set a base output directory in Settings.")
            return

        folder = os.path.join(base, proj.project_id)
        proposal_path = os.path.join(folder, f"{proj.project_id}-proposal.pdf")

        if os.path.exists(proposal_path):
            # Need PIN to override
            dialog = PinEntryDialog(self, "Proposal already exists. Enter PIN to regenerate:")
            self.wait_window(dialog)
            if not dialog.result or not verify_pin(dialog.result):
                show_error("Access Denied", "Incorrect PIN.")
                return

        # Prompt for description/note
        desc_dialog = ProposalTextDialog(self,
                                         existing_desc=proj.proposal_description,
                                         existing_note=proj.proposal_note)
        self.wait_window(desc_dialog)
        if desc_dialog.cancelled:
            return

        update_proposal_texts(self.project_db_id, desc_dialog.description, desc_dialog.note)
        set_binding(self.project_db_id)

        # Reload project with updated texts
        self._project = get_by_id(self.project_db_id)
        proj = self._project
        clients = clients_for_project(self.project_db_id)
        services = services_for_project(self.project_db_id)
        financials = get_financials(self.project_db_id)
        company_info = get_company_info(proj.company)

        os.makedirs(folder, exist_ok=True)
        try:
            generate_proposal(proposal_path, proj, clients, services, financials, company_info)
            show_info("Proposal Generated", f"Proposal saved:\n{os.path.basename(proposal_path)}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate proposal:\n{e}")

        self.refresh()

    def _generate_master(self):
        proj = self._project
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if not base:
            show_error("No Output Directory", "Set a base output directory in Settings.")
            return

        desc_dialog = MasterTextDialog(self,
                                       existing_desc=proj.master_description,
                                       existing_note=proj.master_note)
        self.wait_window(desc_dialog)
        if desc_dialog.cancelled:
            return

        update_master_texts(self.project_db_id, desc_dialog.description, desc_dialog.note)
        self._project = get_by_id(self.project_db_id)
        proj = self._project

        folder = os.path.join(base, proj.project_id)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"MASTER-{proj.project_id}.pdf")

        clients = clients_for_project(self.project_db_id)
        services = services_for_project(self.project_db_id)
        payments = payments_for_project(self.project_db_id)
        financials = get_financials(self.project_db_id)
        company_info = get_company_info(proj.company)

        try:
            generate_master(path, proj, clients, services, payments, financials, company_info)
            show_info("Master File Generated", f"Saved:\n{os.path.basename(path)}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate master file:\n{e}")

    def _open_quote(self):
        QuoteFormDialog(self, self.project_db_id)

    def _open_service_form(self, service_type: str):
        ServiceFormDialog(self, self.project_db_id, service_type, on_save=self.refresh)

    def _open_payment_form(self):
        PaymentFormDialog(self, self.project_db_id, on_save=self.refresh)

    def _mark_paid(self, payment):
        set_paid(payment.id)

        # Generate receipt PDF
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        proj = self._project
        if base:
            folder = os.path.join(base, proj.project_id)
            os.makedirs(folder, exist_ok=True)
            filename = f"REC-{proj.project_id}-{payment.id:04d}.pdf"
            path = os.path.join(folder, filename)
            clients = clients_for_project(self.project_db_id)
            financials = get_financials(self.project_db_id)
            company_info = get_company_info(proj.company)
            updated_payment = get_payment(payment.id)
            try:
                generate_receipt(path, proj, updated_payment, clients, financials, company_info)
                show_info("Receipt Generated", f"Paid receipt saved:\n{filename}")
            except Exception as e:
                show_error("PDF Error", f"Receipt could not be generated:\n{e}")

        self.refresh()


class ProposalTextDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_desc="", existing_note=""):
        super().__init__(parent)
        self.cancelled = False
        self.description = ""
        self.note = ""
        self.title("Proposal Details")
        self.geometry("460x380")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(existing_desc, existing_note)

    def _build_ui(self, desc, note):
        label(self, "Proposal Details", bold=True, size=15).pack(pady=(20, 4))

        section_label(self, "GENERAL DESCRIPTION (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._desc = ctk.CTkTextbox(self, width=400, height=90, corner_radius=8)
        self._desc.pack(padx=24)
        if desc:
            self._desc.insert("1.0", desc)

        section_label(self, "NOTE (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._note = ctk.CTkTextbox(self, width=400, height=90, corner_radius=8)
        self._note.pack(padx=24)
        if note:
            self._note.insert("1.0", note)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=16)
        button(row, "Continue", self._submit, width=130,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=8)
        button(row, "Cancel", self._cancel, width=100,
               fg_color="gray", hover_color="#555").pack(side="left", padx=8)

    def _submit(self):
        self.description = self._desc.get("1.0", "end").strip()
        self.note = self._note.get("1.0", "end").strip()
        self.destroy()

    def _cancel(self):
        self.cancelled = True
        self.destroy()


class MasterTextDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_desc="", existing_note=""):
        super().__init__(parent)
        self.cancelled = False
        self.description = ""
        self.note = ""
        self.title("Master File Details")
        self.geometry("460x380")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(existing_desc, existing_note)

    def _build_ui(self, desc, note):
        label(self, "Master File Details", bold=True, size=15).pack(pady=(20, 4))

        section_label(self, "GENERAL DESCRIPTION (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._desc = ctk.CTkTextbox(self, width=400, height=90, corner_radius=8)
        self._desc.pack(padx=24)
        if desc:
            self._desc.insert("1.0", desc)

        section_label(self, "NOTE (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._note = ctk.CTkTextbox(self, width=400, height=90, corner_radius=8)
        self._note.pack(padx=24)
        if note:
            self._note.insert("1.0", note)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=16)
        button(row, "Generate", self._submit, width=130,
               fg_color="#4a90d9", hover_color="#2c6faf").pack(side="left", padx=8)
        button(row, "Cancel", self._cancel, width=100,
               fg_color="gray", hover_color="#555").pack(side="left", padx=8)

    def _submit(self):
        self.description = self._desc.get("1.0", "end").strip()
        self.note = self._note.get("1.0", "end").strip()
        self.destroy()

    def _cancel(self):
        self.cancelled = True
        self.destroy()
