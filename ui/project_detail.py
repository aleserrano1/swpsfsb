"""Project detail view with Overview, Services, and Payments tabs."""
import os
import customtkinter as ctk
import tkinter.messagebox as mb

import config
from models.project import get_by_id, get_financials, set_binding, set_completed, update_proposal_texts, update_master_texts, update_color
from models.client import (
    clients_for_project,
    search_names, search_emails, search_phones,
    search_address_line1, search_address_line2,
    search_cities, search_states, search_zip_codes,
)
from models.service import services_for_project, delete_service, add_subfield, delete_subfield, toggle_hidden
from models.payment import payments_for_project, mark_paid, delete_payment, get_by_id as get_payment
from models.settings import get_company_info, verify_pin
from models.phone import sanitize as sanitize_phone, format_display as format_phone
from pdf.proposal import generate as generate_proposal
from pdf.change_order import generate as generate_change_order
from pdf.invoice import generate_receipt
from pdf.master import generate as generate_master
from ui.theme import COLOR_THEMES, COMPANY_LABELS, STATUS_LABELS, STATUS_COLORS
from ui.widgets import label, button, entry, section_label, textbox, show_error, show_info, ask_yes_no, AutocompleteEntry
from ui.service_form import ServiceFormDialog
from ui.payment_form import PaymentFormDialog
from ui.quote_form import QuoteFormDialog
from ui.startup import PinEntryDialog



def _format_address_lines(addr: dict) -> list[str]:
    lines = []
    if addr.get("line1"):
        lines.append(addr["line1"])
    if addr.get("line2"):
        lines.append(addr["line2"])
    city_state = ", ".join(filter(None, [addr.get("city"), addr.get("state")]))
    zip_code = addr.get("zip_code", "")
    last = f"{city_state} {zip_code}".strip() if zip_code else city_state
    if last:
        lines.append(last)
    return lines


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
        active_tab = self._tabview.get() if hasattr(self, "_tabview") else None
        self._load()
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        if active_tab:
            def _restore(tab=active_tab):
                try:
                    self._tabview.set(tab)
                except Exception:
                    pass
            self.after(0, _restore)

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

        status = proj.status
        is_binding = status == "binding"
        is_completed = status == "completed"

        if is_completed:
            pass  # no transition buttons on completed projects
        elif is_binding:
            button(actions, "Generate Change Order", self._generate_change_order, width=185,
                   fg_color="#fb8c00", hover_color="#e65100").pack(side="left", padx=(0, 8))
            button(actions, "Mark as Completed", self._mark_completed, width=160,
                   fg_color="#546e7a", hover_color="#37474f").pack(side="left", padx=(0, 8))
        else:
            button(actions, "Generate Proposal", self._generate_proposal, width=160,
                   fg_color="#4a90d9", hover_color="#2c6faf").pack(side="left", padx=(0, 8))
            button(actions, "Mark as Binding", self._mark_binding, width=160,
                   fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=(0, 8))
        button(actions, "Generate Master File", self._generate_master, width=180).pack(side="left", padx=(0, 8))
        if not is_completed:
            button(actions, "Generate Quote", self._open_quote, width=140,
                   fg_color="#8e44ad", hover_color="#6a1f82").pack(side="left")

        # ── Tabs ─────────────────────────────────────────────────────────────
        self._tabview = ctk.CTkTabview(
            self,
            anchor="w",
            fg_color="#262c40",
            segmented_button_fg_color="#262c40",
            segmented_button_selected_color="#7e67f5",
            segmented_button_selected_hover_color="#6952d4",
            segmented_button_unselected_color="#262c40",
            segmented_button_unselected_hover_color="#1a2540",
            text_color="#ffffff",
            text_color_disabled="#8292a1",
        )
        self._tabview.pack(fill="both", expand=True, padx=32, pady=12)
        self._tabview.add("Overview")
        self._tabview.add("Services")
        self._tabview.add("Payments")

        self._tabview._segmented_button.configure(
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=12,
        )

        self._build_overview_tab(self._tabview.tab("Overview"))
        self._build_services_tab(self._tabview.tab("Services"))
        self._build_payments_tab(self._tabview.tab("Payments"))

    # ── Overview Tab ────────────────────────────────────────────────────────

    def _build_overview_tab(self, tab):
        is_completed = self._project.status == "completed"
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        CARD_BG = "#0d1826"
        CARD_RADIUS = 16
        PX = 16
        PY = 12

        # ── Clients card ─────────────────────────────────────────────────
        clients_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        clients_card.pack(fill="x", pady=(8, 6))

        clients_title_row = ctk.CTkFrame(clients_card, fg_color="transparent")
        clients_title_row.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(clients_title_row, "CLIENTS").pack(side="left")

        for i, client in enumerate(self._clients):
            if i > 0:
                ctk.CTkFrame(clients_card, height=1, fg_color="#1a2540").pack(fill="x", padx=PX, pady=(4, 0))

            client_hdr = ctk.CTkFrame(clients_card, fg_color="transparent")
            client_hdr.pack(fill="x", padx=PX, pady=(4 if i > 0 else 0, 0))
            if len(self._clients) > 1:
                label(client_hdr, f"Client {i+1}", bold=True, size=12).pack(side="left")
            if not is_completed:
                button(client_hdr, "Edit", lambda c=client: self._open_edit_client(c),
                       width=60, height=24, fg_color="#4a90d9", hover_color="#2c6faf").pack(side="right")

            is_last = i == len(self._clients) - 1
            inner = ctk.CTkFrame(clients_card, fg_color="transparent")
            inner.pack(anchor="w", padx=PX, pady=(2, PY if is_last else 6))
            if client.names:
                label(inner, ", ".join(client.names), bold=True, size=13).pack(anchor="w")
            for email in client.emails:
                label(inner, email, size=11, fg="gray").pack(anchor="w")
            for phone in client.phones:
                label(inner, format_phone(phone), size=11, fg="gray").pack(anchor="w")
            for addr in client.addresses:
                for line in _format_address_lines(addr):
                    label(inner, line, size=11, fg="gray").pack(anchor="w")

        # ── Job Site card ─────────────────────────────────────────────────
        js_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        js_card.pack(fill="x", pady=6)

        js_title_row = ctk.CTkFrame(js_card, fg_color="transparent")
        js_title_row.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(js_title_row, "JOB SITE").pack(side="left")
        if not is_completed:
            button(js_title_row, "Edit", self._open_edit_job_site,
                   width=60, height=24, fg_color="#4a90d9", hover_color="#2c6faf").pack(side="right")

        js_body = ctk.CTkFrame(js_card, fg_color="transparent")
        js_body.pack(anchor="w", padx=PX, pady=(0, PY))
        js_lines = _format_address_lines(self._project.job_site)
        for line in (js_lines or ["—"]):
            label(js_body, line, size=12).pack(anchor="w")

        # ── Project Details card (tax rate) ───────────────────────────────
        details_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        details_card.pack(fill="x", pady=6)

        details_title_row = ctk.CTkFrame(details_card, fg_color="transparent")
        details_title_row.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(details_title_row, "PROJECT DETAILS").pack(side="left")

        details_body = ctk.CTkFrame(details_card, fg_color="transparent")
        details_body.pack(anchor="w", padx=PX, pady=(0, PY))
        tax_row = ctk.CTkFrame(details_body, fg_color="transparent")
        tax_row.pack(anchor="w")
        label(tax_row, "Tax Rate:", size=12, fg="gray").pack(side="left", padx=(0, 10))
        if is_completed:
            label(tax_row, f"{self._project.tax_rate}%", size=12).pack(side="left")
        else:
            self._tax_rate_entry = ctk.CTkEntry(
                tax_row, width=100, placeholder_text="e.g. 8.5",
                fg_color="#1b2333", border_color="#7e67f5", border_width=2,
                corner_radius=10, placeholder_text_color="#8292a1",
            )
            self._tax_rate_entry.insert(0, str(self._project.tax_rate))
            self._tax_rate_entry.pack(side="left", padx=(0, 8))
            button(tax_row, "Update", self._save_tax_rate, width=80, height=28).pack(side="left")

        # ── Financial Summary card ────────────────────────────────────────
        fin_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        fin_card.pack(fill="x", pady=(6, 8))

        fin_title_row = ctk.CTkFrame(fin_card, fg_color="transparent")
        fin_title_row.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(fin_title_row, "FINANCIAL SUMMARY").pack(side="left")

        fin = self._financials
        fin_rows = [
            ("Subtotal",          f"${fin['subtotal']:,.2f}"),
            (f"Tax ({fin['tax_rate']:.1f}%)", f"${fin['tax']:,.2f}"),
            ("Project Total",     f"${fin['total']:,.2f}"),
            ("Total Paid",        f"${fin['paid']:,.2f}"),
            ("Balance Remaining", f"${fin['balance']:,.2f}"),
        ]
        for i, (lbl_text, val_text) in enumerate(fin_rows):
            is_bold = lbl_text in ("Project Total", "Balance Remaining")
            row_bg = "#1a2540" if i % 2 == 0 else "#0f1a2e"
            row = ctk.CTkFrame(fin_card, corner_radius=8, fg_color=row_bg)
            row.pack(fill="x", padx=PX, pady=2)
            label(row, lbl_text, size=12, bold=is_bold).pack(side="left", padx=12, pady=8)
            label(row, val_text, size=12, bold=is_bold).pack(side="right", padx=12, pady=8)
        ctk.CTkFrame(fin_card, fg_color="transparent", height=PY).pack()

    # ── Services Tab ────────────────────────────────────────────────────────

    def _build_services_tab(self, tab):
        status = self._project.status
        is_binding = status == "binding"
        is_completed = status == "completed"

        CARD_BG = "#0d1826"
        CARD_RADIUS = 16
        PX = 16
        PY = 12

        # ── Top action bar ────────────────────────────────────────────────
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))

        button(
            top, "+ Add Service",
            lambda: self._open_service_form("original_service"),
            width=140,
            fg_color="#4caf50" if not is_binding and not is_completed else "gray",
            hover_color="#2e7d32" if not is_binding and not is_completed else "gray",
            state="normal" if not is_binding and not is_completed else "disabled",
        ).pack(side="left", padx=(0, 8))

        button(
            top, "+ Add Change Order",
            lambda: self._open_service_form("order_change"),
            width=170,
            fg_color="#fb8c00" if is_binding else "gray",
            hover_color="#e65100" if is_binding else "gray",
            state="normal" if is_binding else "disabled",
        ).pack(side="left", padx=(0, 8))

        if is_completed:
            hint = "Project is completed — no further service changes allowed."
        elif is_binding:
            hint = "Project is binding — add Change Orders only."
        else:
            hint = "Change Orders available after marking Binding."
        label(top, hint, size=11, fg="gray").pack(side="left")

        # ── Down Payment card ─────────────────────────────────────────────
        dp_card = ctk.CTkFrame(tab, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        dp_card.pack(fill="x", pady=(8, 4))
        dp_inner = ctk.CTkFrame(dp_card, fg_color="transparent")
        dp_inner.pack(fill="x", padx=PX, pady=PY)
        section_label(dp_inner, "DOWN PAYMENT ($)").pack(side="left", padx=(0, 10))
        if is_completed:
            label(dp_inner, f"${self._project.down_payment:,.2f}", size=12).pack(side="left")
        else:
            self._dp_entry = ctk.CTkEntry(
                dp_inner, width=130, placeholder_text="e.g. 1500",
                fg_color="#1b2333", border_color="#7e67f5", border_width=2,
                corner_radius=10, placeholder_text_color="#8292a1",
            )
            self._dp_entry.insert(0, str(self._project.down_payment))
            self._dp_entry.pack(side="left", padx=(0, 8))
            button(dp_inner, "Update", self._save_down_payment,
                   width=80, height=28).pack(side="left")

        # ── Scrollable content ────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=4)

        originals = [s for s in self._services if s.type == "original_service"]
        changes = [s for s in self._services if s.type == "order_change"]

        # ── Original Services card ────────────────────────────────────────
        orig_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        orig_card.pack(fill="x", pady=(4, 6))

        orig_hdr = ctk.CTkFrame(orig_card, fg_color="transparent")
        orig_hdr.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(orig_hdr, "ORIGINAL SERVICES").pack(side="left")

        if originals:
            for svc in originals:
                self._service_row(orig_card, svc)
        else:
            label(orig_card, "No original services added yet.", size=11, fg="gray").pack(
                anchor="w", padx=PX, pady=(0, PY))
        ctk.CTkFrame(orig_card, fg_color="transparent", height=PY).pack()

        # ── Change Orders card ────────────────────────────────────────────
        co_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        co_card.pack(fill="x", pady=6)

        co_hdr = ctk.CTkFrame(co_card, fg_color="transparent")
        co_hdr.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(co_hdr, "CHANGE ORDERS").pack(side="left")

        if changes:
            for svc in changes:
                self._service_row(co_card, svc, accent_color="#fb8c00")
        else:
            empty_msg = (
                "No change orders added yet."
                if is_binding
                else "Change Orders available after marking project as Binding."
            )
            label(co_card, empty_msg, size=11, fg="gray").pack(
                anchor="w", padx=PX, pady=(0, PY))
        ctk.CTkFrame(co_card, fg_color="transparent", height=PY).pack()

        # ── Totals card ───────────────────────────────────────────────────
        fin = self._financials
        totals_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
        totals_card.pack(fill="x", pady=(6, 8))

        totals_hdr = ctk.CTkFrame(totals_card, fg_color="transparent")
        totals_hdr.pack(fill="x", padx=PX, pady=(PY, 8))
        section_label(totals_hdr, "TOTALS").pack(side="left")

        for i, (lbl_text, val_text) in enumerate([
            ("Subtotal",                f"${fin['subtotal']:,.2f}"),
            (f"Tax ({fin['tax_rate']:.1f}%)", f"${fin['tax']:,.2f}"),
            ("Total",                   f"${fin['total']:,.2f}"),
        ]):
            row_bg = "#1a2540" if i % 2 == 0 else "#0f1a2e"
            row = ctk.CTkFrame(totals_card, corner_radius=8, fg_color=row_bg)
            row.pack(fill="x", padx=PX, pady=2)
            label(row, lbl_text, size=12).pack(side="left", padx=12, pady=8)
            label(row, val_text, size=12, bold=(lbl_text == "Total")).pack(side="right", padx=12, pady=8)
        ctk.CTkFrame(totals_card, fg_color="transparent", height=PY).pack()

    def _service_row(self, parent, svc, accent_color="#4a90d9"):
        is_completed = self._project.status == "completed"
        hidden_bg = "#0d1520"
        card = ctk.CTkFrame(parent, corner_radius=10,
                            fg_color=hidden_bg if svc.is_hidden else "#131f30")
        card.pack(fill="x", padx=16, pady=3)

        # Header row: description + amount + hide + delete
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        desc_color = "gray" if svc.is_hidden else None
        label(header, svc.description, size=12, fg=desc_color).pack(side="left", anchor="w")

        amt_label = label(header, f"${svc.amount:,.2f}", bold=True, size=12,
                          fg="gray" if svc.is_hidden else None)
        amt_label.pack(side="right")

        if not is_completed:
            button(header, "Delete", lambda s=svc: self._delete_service(s),
                   width=70, height=24, fg_color="#e53935", hover_color="#b71c1c").pack(side="right", padx=8)

            hide_label = "Show" if svc.is_hidden else "Hide"
            hide_btn = button(header, hide_label, None,
                              width=56, height=24, fg_color="#757575", hover_color="#424242")
            hide_btn.pack(side="right", padx=(0, 4))

            def _toggle_hidden(s=svc):
                toggle_hidden(s.id)
                self._maybe_regenerate_master()
                self.refresh()

            hide_btn.configure(command=_toggle_hidden)

        if svc.is_hidden:
            ctk.CTkLabel(header, text="HIDDEN", font=ctk.CTkFont(size=9),
                         fg_color="#757575", text_color="white",
                         corner_radius=4, padx=4, pady=1).pack(side="left", padx=(6, 0))

        # Subfields area — hidden when service is hidden
        sf_container = ctk.CTkFrame(card, fg_color="transparent")
        if not svc.is_hidden:
            sf_container.pack(fill="x", padx=(28, 12), pady=(0, 4))

        is_original_on_binding = (
            self._project.status == "binding" and svc.type == "original_service"
        )

        def _render_subfields():
            for w in sf_container.winfo_children():
                w.destroy()
            for sf in svc.subfields:
                sf_row = ctk.CTkFrame(sf_container, fg_color="transparent")
                sf_row.pack(fill="x", pady=1)
                label(sf_row, f"• {sf.text}", size=11, fg="gray").pack(side="left", anchor="w")

                if not is_completed:
                    def _del_sf(sf_id=sf.id):
                        if not self._verify_pin_for_binding("Enter PIN to delete this subfield:"):
                            return
                        delete_subfield(sf_id, authorized=True)
                        svc.subfields = [s for s in svc.subfields if s.id != sf_id]
                        _render_subfields()

                    button(sf_row, "×", _del_sf, width=24, height=20,
                           fg_color="#e53935", hover_color="#b71c1c").pack(side="right", padx=2)

            if is_completed:
                pass  # read-only — no add row
            elif is_original_on_binding:
                lock_row = ctk.CTkFrame(sf_container, fg_color="transparent")
                lock_row.pack(fill="x", pady=(2, 0))
                label(lock_row, "Sub-lines locked — cannot add to original services while project is binding.",
                      size=10, fg="#fb8c00").pack(side="left")
            else:
                # Inline "add subfield" row
                add_row = ctk.CTkFrame(sf_container, fg_color="transparent")
                add_row.pack(fill="x", pady=(2, 0))
                sf_entry = ctk.CTkEntry(
                    add_row, placeholder_text="Add subfield detail...",
                    height=26, corner_radius=10,
                    fg_color="#1b2333", border_color="#7e67f5", border_width=2,
                    placeholder_text_color="#8292a1",
                )
                sf_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

                def _add_sf():
                    text = sf_entry.get().strip()
                    if not text:
                        return
                    try:
                        new_sf = add_subfield(svc.id, text, sort_order=len(svc.subfields))
                    except ValueError as exc:
                        show_error("Not Allowed", str(exc))
                        return
                    svc.subfields.append(new_sf)
                    _render_subfields()

                button(add_row, "+", _add_sf, width=28, height=26,
                       fg_color=accent_color, hover_color="#1565c0").pack(side="right")

        _render_subfields()

    def _verify_pin_for_binding(self, prompt: str) -> bool:
        """Return True if the project is non-binding or the user enters the correct PIN."""
        if self._project.status != "binding":
            return True
        dialog = PinEntryDialog(self, prompt)
        self.wait_window(dialog)
        if not dialog.result or not verify_pin(dialog.result):
            show_error("Access Denied", "Incorrect PIN. Deletion cancelled.")
            return False
        return True

    def _delete_service(self, svc):
        if not ask_yes_no("Delete Service", f"Delete '{svc.description}'?"):
            return
        if not self._verify_pin_for_binding("Enter PIN to delete this line item:"):
            return
        delete_service(svc.id, authorized=True)
        self._maybe_regenerate_master()
        self.refresh()

    def _save_down_payment(self):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        try:
            val = float(self._dp_entry.get().strip() or "0")
        except ValueError:
            show_error("Invalid Amount", "Down payment must be a number.")
            return
        from models.project import update_down_payment
        update_down_payment(self.project_db_id, val)
        self._maybe_regenerate_master()
        self.refresh()

    # ── Payments Tab ────────────────────────────────────────────────────────

    def _build_payments_tab(self, tab):
        status = self._project.status

        if status == "non_binding":
            wrapper = ctk.CTkFrame(tab, fg_color="transparent")
            wrapper.pack(fill="both", expand=True)
            label(wrapper, "Payments Locked", size=16, bold=True, fg="#fb8c00").pack(pady=(40, 8))
            label(
                wrapper,
                "This project must be marked as Binding before payments can be created.",
                size=13,
                fg="gray",
            ).pack()
            return

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))
        if status == "binding":
            button(top, "+ Add Payment", self._open_payment_form, width=140,
                   fg_color="#4caf50", hover_color="#2e7d32").pack(side="left")

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=4)

        if not self._payments:
            label(scroll, "No payments recorded.", fg="gray", size=13).pack(pady=20)
            return

        for pmt in self._payments:
            self._payment_row(scroll, pmt)

        # Balance summary card
        fin = self._financials
        bal_card = ctk.CTkFrame(scroll, corner_radius=16, fg_color="#0d1826")
        bal_card.pack(fill="x", pady=(12, 8))

        bal_hdr = ctk.CTkFrame(bal_card, fg_color="transparent")
        bal_hdr.pack(fill="x", padx=16, pady=(12, 8))
        section_label(bal_hdr, "BALANCE SUMMARY").pack(side="left")

        for i, (lbl_text, val_text) in enumerate([
            ("Project Total", f"${fin['total']:,.2f}"),
            ("Total Paid",    f"${fin['paid']:,.2f}"),
            ("Balance",       f"${fin['balance']:,.2f}"),
        ]):
            row_bg = "#1a2540" if i % 2 == 0 else "#0f1a2e"
            row = ctk.CTkFrame(bal_card, corner_radius=8, fg_color=row_bg)
            row.pack(fill="x", padx=16, pady=2)
            label(row, lbl_text, size=12).pack(side="left", padx=12, pady=8)
            label(row, val_text, size=12, bold=(lbl_text == "Balance")).pack(side="right", padx=12, pady=8)
        ctk.CTkFrame(bal_card, fg_color="transparent", height=12).pack()

    def _payment_row(self, parent, pmt):
        status_color = "#4caf50" if pmt.status == "paid" else "#fb8c00"
        row = ctk.CTkFrame(parent, corner_radius=12, fg_color="#0d1826")
        row.pack(fill="x", pady=3)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        # Left: description + meta + allocations
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        label(info, pmt.description or f"Invoice #{pmt.id}", size=12, bold=True).pack(anchor="w")
        meta_parts = []
        if pmt.payment_type:
            meta_parts.append(pmt.payment_type)
        if pmt.payment_description:
            meta_parts.append(pmt.payment_description)
        meta_parts.append(pmt.created_at[:10])
        label(info, "  •  ".join(meta_parts), size=11, fg="gray").pack(anchor="w")

        if pmt.allocations:
            svc_map = {s.id: s for s in self._services}
            for alloc in pmt.allocations:
                svc = svc_map.get(alloc.service_id)
                svc_name = svc.description if svc else f"Service #{alloc.service_id}"
                label(info, f"  └ ${alloc.amount:,.2f} → {svc_name}", size=11, fg="gray").pack(anchor="w")

        # Right: amount + status + mark paid
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        label(right, f"${pmt.amount:,.2f}", bold=True, size=13).pack(anchor="e")
        ctk.CTkLabel(right, text=pmt.status.upper(),
                     font=ctk.CTkFont(size=10), fg_color=status_color,
                     text_color="white", corner_radius=6, padx=6, pady=2).pack(anchor="e", pady=2)
        if pmt.status == "unpaid" and self._project.status != "completed":
            button(right, "Mark Paid", lambda p=pmt: self._mark_paid(p),
                   width=100, height=26, fg_color="#4a90d9", hover_color="#2c6faf").pack(anchor="e", pady=2)
            button(right, "Delete", lambda p=pmt: self._delete_payment(p),
                   width=100, height=26, fg_color="#e53935", hover_color="#b71c1c").pack(anchor="e", pady=2)

    # ── Overview edit helpers ────────────────────────────────────────────────

    def _open_edit_client(self, client):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        EditClientDialog(self, client, on_save=self.refresh)

    def _open_edit_job_site(self):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        EditJobSiteDialog(self, self.project_db_id, self._project.job_site, on_save=self.refresh)

    def _save_tax_rate(self):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        try:
            val = float(self._tax_rate_entry.get().strip())
        except ValueError:
            show_error("Invalid Rate", "Tax rate must be a number.")
            return
        from models.project import update_tax_rate
        update_tax_rate(self.project_db_id, val)
        self._maybe_regenerate_master()
        self.refresh()

    # ── Actions ─────────────────────────────────────────────────────────────

    def _change_color(self, color_name: str):
        update_color(self.project_db_id, color_name)
        self.refresh()

    def _generate_proposal(self):
        proj = self._project
        if proj.status == "binding":
            show_info(
                "Cannot Generate Proposal",
                "Proposals cannot be regenerated once a project is marked as binding.",
            )
            return

        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if not base:
            show_error("No Output Directory", "Set a base output directory in Settings.")
            return

        desc_dialog = ProposalTextDialog(self,
                                         existing_desc=proj.proposal_description,
                                         existing_note=proj.proposal_note)
        self.wait_window(desc_dialog)
        if desc_dialog.cancelled:
            return

        update_proposal_texts(self.project_db_id, desc_dialog.description, desc_dialog.note)
        self._project = get_by_id(self.project_db_id)
        proj = self._project

        clients = clients_for_project(self.project_db_id)
        services = [
            s for s in services_for_project(self.project_db_id)
            if not s.is_hidden and s.type == "original_service"
        ]
        financials = get_financials(self.project_db_id)
        company_info = get_company_info(proj.company)

        folder = os.path.join(base, proj.project_id)
        proposal_path = os.path.join(folder, f"{proj.project_id}-proposal.pdf")
        os.makedirs(folder, exist_ok=True)
        try:
            generate_proposal(proposal_path, proj, clients, services, financials, company_info)
            show_info("Proposal Generated", f"Proposal saved:\n{os.path.basename(proposal_path)}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate proposal:\n{e}")

        self._maybe_regenerate_master()
        self.refresh()

    def _generate_change_order(self):
        proj = self._project
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if not base:
            show_error("No Output Directory", "Set a base output directory in Settings.")
            return

        services = [
            s for s in services_for_project(self.project_db_id)
            if not s.is_hidden and s.type == "order_change"
        ]
        if not services:
            show_error("No Change Orders", "There are no visible change order items to include.")
            return

        clients = clients_for_project(self.project_db_id)
        company_info = get_company_info(proj.company)

        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        folder = os.path.join(base, proj.project_id)
        filename = f"CO-{proj.project_id}-{ts}.pdf"
        path = os.path.join(folder, filename)
        os.makedirs(folder, exist_ok=True)
        try:
            generate_change_order(path, proj, clients, services, company_info)
            show_info("Change Order Generated", f"Saved:\n{filename}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate change order:\n{e}")
            return

        self._maybe_regenerate_master()

    def _mark_binding(self):
        proj = self._project
        if proj.status == "binding":
            show_info("Already Binding", "This project is already binding.")
            return

        if not ask_yes_no(
            "Mark as Binding",
            "Mark this project as binding?\n\nOriginal services will be locked and proposal generation will be disabled.",
        ):
            return

        set_binding(self.project_db_id)
        show_info("Project Binding", "Project has been marked as binding.")
        self.refresh()

    def _mark_completed(self):
        proj = self._project
        if proj.status == "completed":
            show_info("Already Completed", "This project is already completed.")
            return

        fin = get_financials(self.project_db_id)
        if abs(fin["balance"]) > 0.005:
            show_error(
                "Balance Outstanding",
                f"This project cannot be marked as completed until the balance is fully paid.\n\n"
                f"Remaining balance: ${fin['balance']:,.2f}",
            )
            return

        if not ask_yes_no(
            "Mark as Completed",
            "Mark this project as completed?\n\nNo further services or payments can be added after this.",
        ):
            return

        set_completed(self.project_db_id)
        show_info("Project Completed", "Project has been marked as completed.")
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

    def _maybe_regenerate_master(self):
        """Silently regenerate the master file if it already exists on disk."""
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if not base:
            return
        proj = get_by_id(self.project_db_id)
        if not proj:
            return
        folder = os.path.join(base, proj.project_id)
        master_path = os.path.join(folder, f"MASTER-{proj.project_id}.pdf")
        if not os.path.exists(master_path):
            return
        try:
            clients = clients_for_project(self.project_db_id)
            services = services_for_project(self.project_db_id)
            payments = payments_for_project(self.project_db_id)
            financials = get_financials(self.project_db_id)
            company_info = get_company_info(proj.company)
            generate_master(master_path, proj, clients, services, payments, financials, company_info)
        except Exception:
            pass

    def _open_quote(self):
        if self._project.status == "completed":
            show_error("Not Allowed", "Quotes cannot be generated for completed projects.")
            return
        QuoteFormDialog(self, self.project_db_id, on_done=self._maybe_regenerate_master)

    def _open_service_form(self, service_type: str):
        status = self._project.status
        if status == "completed":
            show_error("Not Allowed", "This project is completed. No further services can be added.")
            return
        if status == "non_binding" and service_type == "order_change":
            show_error("Not Allowed", "Change Orders can only be added after the project is marked as Binding.")
            return
        if status == "binding" and service_type == "original_service":
            show_error("Not Allowed", "Original Services cannot be added to a binding project. Use a Change Order instead.")
            return

        def _on_save():
            self._maybe_regenerate_master()
            self.refresh()

        ServiceFormDialog(self, self.project_db_id, service_type, on_save=_on_save)

    def _open_payment_form(self):
        def _on_save():
            self._maybe_regenerate_master()
            self.refresh()

        PaymentFormDialog(self, self.project_db_id, on_save=_on_save)

    def _mark_paid(self, payment):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        dialog = MarkPaidDialog(self, payment)
        self.wait_window(dialog)
        if dialog.cancelled:
            return

        updated_payment = mark_paid(payment.id, dialog.payment_type, dialog.payment_description)

        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        proj = self._project
        if base:
            folder = os.path.join(base, proj.project_id)
            os.makedirs(folder, exist_ok=True)

            inv_filename = f"INV-{proj.project_id}-{payment.id:04d}.pdf"
            inv_path = os.path.join(folder, inv_filename)
            inv_existed = os.path.exists(inv_path)
            if inv_existed:
                try:
                    os.remove(inv_path)
                except Exception:
                    pass

            rec_filename = f"REC-{proj.project_id}-{payment.id:04d}.pdf"
            rec_path = os.path.join(folder, rec_filename)
            clients = clients_for_project(self.project_db_id)
            financials = get_financials(self.project_db_id)
            company_info = get_company_info(proj.company)
            svcs = services_for_project(self.project_db_id)
            try:
                generate_receipt(rec_path, proj, updated_payment, clients, financials, company_info, services=svcs)
                if inv_existed:
                    show_info("Receipt Generated", f"Invoice replaced with paid receipt:\n{rec_filename}")
                else:
                    show_info(
                        "Receipt Generated",
                        f"Original invoice PDF was not found.\n"
                        f"A new paid receipt was created:\n{rec_filename}",
                    )
            except Exception as e:
                show_error("PDF Error", f"Receipt could not be generated:\n{e}")

        self._maybe_regenerate_master()
        self.refresh()

    def _delete_payment(self, payment):
        if self._project.status == "completed":
            show_error("Not Allowed", "This project is completed and cannot be modified.")
            return
        if not ask_yes_no(
            "Delete Invoice",
            f"Delete invoice for ${payment.amount:,.2f}?\nThis cannot be undone.",
        ):
            return
        try:
            delete_payment(payment.id)
        except ValueError as e:
            show_error("Cannot Delete", str(e))
            return

        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        proj = self._project
        if base:
            inv_filename = f"INV-{proj.project_id}-{payment.id:04d}.pdf"
            inv_path = os.path.join(base, proj.project_id, inv_filename)
            if os.path.exists(inv_path):
                try:
                    os.remove(inv_path)
                except Exception as e:
                    show_error("File Error", f"Invoice deleted from records, but the PDF could not be removed:\n{e}")
            else:
                show_info("PDF Not Found", f"Invoice deleted from records, but the PDF file was not found:\n{inv_filename}")

        self._maybe_regenerate_master()
        self.refresh()


class ProposalTextDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_desc="", existing_note=""):
        super().__init__(parent)
        self.configure(fg_color="#262c40")
        self.cancelled = False
        self.description = ""
        self.note = ""
        self.title("Proposal Details")
        self.geometry("460x380")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(existing_desc, existing_note)

    def _build_ui(self, desc, note):
        label(self, "Proposal Details", bold=True, size=15, fg="#ffffff").pack(pady=(20, 4))

        section_label(self, "GENERAL DESCRIPTION (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._desc = textbox(self, width=400, height=90)
        self._desc.pack(padx=24)
        if desc:
            self._desc.insert("1.0", desc)

        section_label(self, "NOTE (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._note = textbox(self, width=400, height=90)
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
        self.configure(fg_color="#262c40")
        self.cancelled = False
        self.description = ""
        self.note = ""
        self.title("Master File Details")
        self.geometry("460x380")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(existing_desc, existing_note)

    def _build_ui(self, desc, note):
        label(self, "Master File Details", bold=True, size=15, fg="#ffffff").pack(pady=(20, 4))

        section_label(self, "GENERAL DESCRIPTION (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._desc = textbox(self, width=400, height=90)
        self._desc.pack(padx=24)
        if desc:
            self._desc.insert("1.0", desc)

        section_label(self, "NOTE (optional)").pack(anchor="w", padx=24, pady=(8, 2))
        self._note = textbox(self, width=400, height=90)
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


class EditClientDialog(ctk.CTkToplevel):
    def __init__(self, parent, client, on_save):
        super().__init__(parent)
        self.configure(fg_color="#262c40")
        self._client = client
        self._on_save = on_save
        self._name_entries = []
        self._email_entries = []
        self._phone_entries = []
        self._address_blocks = []
        self.title("Edit Client")
        self.geometry("500x580")
        self.resizable(False, True)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        label(self, "Edit Client", bold=True, size=15, fg="#ffffff").pack(pady=(16, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=4)

        self._build_multi_section(scroll, "NAMES", "Full name",
                                  self._client.names, self._name_entries,
                                  make_entry=lambda p, ph: AutocompleteEntry(p, search_names, placeholder=ph, width=380))
        self._build_multi_section(scroll, "EMAILS", "Email address",
                                  self._client.emails, self._email_entries,
                                  make_entry=lambda p, ph: AutocompleteEntry(p, search_emails, placeholder=ph, width=380))
        sanitized_phones = [sanitize_phone(p) for p in (self._client.phones or [])]
        self._build_multi_section(
            scroll, "PHONES", "Phone number",
            sanitized_phones, self._phone_entries,
            make_entry=lambda p, ph: AutocompleteEntry(p, search_phones, placeholder=ph, width=380, phone_mode=True),
        )

        addr_hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        addr_hdr.pack(fill="x", pady=(8, 2))
        section_label(addr_hdr, "ADDRESSES").pack(side="left")
        button(addr_hdr, "+ Add Address", self._add_address_block,
               width=120, height=22, fg_color="#555", hover_color="#333").pack(side="left", padx=8)

        self._addresses_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self._addresses_container.pack(fill="x")

        for addr in (self._client.addresses or [{}]):
            self._add_address_block(addr)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=12)
        button(row, "Save", self._save, width=120,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=8)
        button(row, "Cancel", self.destroy, width=100,
               fg_color="gray", hover_color="#555").pack(side="left", padx=8)

    def _build_multi_section(self, parent, title, placeholder, existing, entry_list, make_entry=None):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", pady=4)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x")
        section_label(header, title).pack(side="left")

        entries_frame = ctk.CTkFrame(container, fg_color="transparent")

        button(header, "+ Add",
               lambda ef=entries_frame, p=placeholder, el=entry_list, me=make_entry: self._add_entry(ef, p, el, me),
               width=80, height=22, fg_color="#555", hover_color="#333").pack(side="left", padx=8)

        entries_frame.pack(fill="x")

        for val in (existing or [""]):
            e = make_entry(entries_frame, placeholder)
            e.pack(anchor="w", pady=1)
            if val:
                e.insert(0, val)
            entry_list.append(e)

    def _add_entry(self, entries_frame, placeholder, entry_list, make_entry=None):
        e = make_entry(entries_frame, placeholder)
        e.pack(anchor="w", pady=1)
        entry_list.append(e)

    def _add_address_block(self, addr=None):
        addr = addr or {}
        block = ctk.CTkFrame(self._addresses_container, fg_color="#1e2d45", corner_radius=12)
        block.pack(fill="x", pady=3)

        inner = ctk.CTkFrame(block, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)

        widgets = {}

        e1 = AutocompleteEntry(inner, search_address_line1, placeholder="Address Line 1 *", width=380)
        e1.pack(anchor="w", pady=1)
        if addr.get("line1"):
            e1.insert(0, addr["line1"])
        widgets["line1"] = e1

        e2 = AutocompleteEntry(inner, search_address_line2, placeholder="Address Line 2 (optional)", width=380)
        e2.pack(anchor="w", pady=1)
        if addr.get("line2"):
            e2.insert(0, addr["line2"])
        widgets["line2"] = e2

        city_row = ctk.CTkFrame(inner, fg_color="transparent")
        city_row.pack(anchor="w", pady=1)

        e_city = AutocompleteEntry(city_row, search_cities, placeholder="City *", width=190)
        e_city.pack(side="left", padx=(0, 6))
        if addr.get("city"):
            e_city.insert(0, addr["city"])
        widgets["city"] = e_city

        e_state = AutocompleteEntry(city_row, search_states, placeholder="State *", width=80)
        e_state.pack(side="left", padx=(0, 6))
        if addr.get("state"):
            e_state.insert(0, addr["state"])
        widgets["state"] = e_state

        e_zip = AutocompleteEntry(city_row, search_zip_codes, placeholder="Zip Code *", width=110)
        e_zip.pack(side="left")
        if addr.get("zip_code"):
            e_zip.insert(0, addr["zip_code"])
        widgets["zip_code"] = e_zip

        button(inner, "Remove Address",
               lambda b=block: self._remove_address_block(b),
               width=130, height=22, fg_color="#e53935", hover_color="#b71c1c").pack(anchor="w", pady=(4, 0))

        self._address_blocks.append({"frame": block, "widgets": widgets})

    def _remove_address_block(self, block_frame):
        self._address_blocks = [b for b in self._address_blocks if b["frame"] is not block_frame]
        block_frame.destroy()

    def _save(self):
        import re

        names = [e.get().strip() for e in self._name_entries if e.get().strip()]
        if not names:
            show_error("Missing Name", "At least one name is required.")
            return

        emails = [e.get().strip() for e in self._email_entries if e.get().strip()]
        phones = [e.get().strip() for e in self._phone_entries if e.get().strip()]

        addresses = []
        for block in self._address_blocks:
            w = block["widgets"]
            addr = {k: w[k].get().strip() for k in w}
            if not any(addr.values()):
                continue
            if not addr.get("line1"):
                show_error("Incomplete Address", "Address Line 1 is required.")
                return
            if not addr.get("city"):
                show_error("Incomplete Address", "City is required.")
                return
            if not addr.get("state"):
                show_error("Incomplete Address", "State is required.")
                return
            zip_val = addr.get("zip_code", "")
            if not zip_val:
                show_error("Incomplete Address", "Zip Code is required.")
                return
            if not re.fullmatch(r"\d{5}(-\d{4})?", zip_val):
                show_error("Invalid Zip Code", f"'{zip_val}' is not a valid zip code.")
                return
            addresses.append(addr)

        from models.client import update_client
        update_client(self._client.id, names, emails, phones, addresses)
        self.destroy()
        self._on_save()


class EditJobSiteDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id, current_job_site, on_save):
        super().__init__(parent)
        self.configure(fg_color="#262c40")
        self._project_db_id = project_db_id
        self._on_save = on_save
        self.title("Edit Job Site")
        self.geometry("460x310")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(current_job_site)

    def _build_ui(self, js):
        label(self, "Edit Job Site", bold=True, size=15, fg="#ffffff").pack(pady=(16, 8))

        frame = ctk.CTkFrame(self, fg_color="#0d1826", corner_radius=16)
        frame.pack(padx=24, fill="x")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=8)

        self._line1 = AutocompleteEntry(inner, search_address_line1, placeholder="Address Line 1 *", width=390)
        self._line1.pack(anchor="w", pady=1)
        if js.get("line1"):
            self._line1.insert(0, js["line1"])

        self._line2 = AutocompleteEntry(inner, search_address_line2, placeholder="Address Line 2 (optional)", width=390)
        self._line2.pack(anchor="w", pady=1)
        if js.get("line2"):
            self._line2.insert(0, js["line2"])

        city_row = ctk.CTkFrame(inner, fg_color="transparent")
        city_row.pack(anchor="w", pady=1)

        self._city = AutocompleteEntry(city_row, search_cities, placeholder="City *", width=190)
        self._city.pack(side="left", padx=(0, 6))
        if js.get("city"):
            self._city.insert(0, js["city"])

        self._state = AutocompleteEntry(city_row, search_states, placeholder="State *", width=80)
        self._state.pack(side="left", padx=(0, 6))
        if js.get("state"):
            self._state.insert(0, js["state"])

        self._zip = AutocompleteEntry(city_row, search_zip_codes, placeholder="Zip *", width=110)
        self._zip.pack(side="left")
        if js.get("zip_code"):
            self._zip.insert(0, js["zip_code"])

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=16)
        button(row, "Save", self._save, width=120,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=8)
        button(row, "Cancel", self.destroy, width=100,
               fg_color="gray", hover_color="#555").pack(side="left", padx=8)

    def _save(self):
        import re
        line1 = self._line1.get().strip()
        line2 = self._line2.get().strip()
        city = self._city.get().strip()
        state = self._state.get().strip()
        zip_code = self._zip.get().strip()

        if not line1:
            show_error("Incomplete Job Site", "Address Line 1 is required.")
            return
        if not city:
            show_error("Incomplete Job Site", "City is required.")
            return
        if not state:
            show_error("Incomplete Job Site", "State is required.")
            return
        if not zip_code:
            show_error("Incomplete Job Site", "Zip Code is required.")
            return
        if not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
            show_error("Invalid Zip Code", f"'{zip_code}' is not a valid zip code.")
            return

        from models.project import update_job_site
        update_job_site(self._project_db_id, {
            "line1": line1, "line2": line2,
            "city": city, "state": state, "zip_code": zip_code,
        })
        self.destroy()
        self._on_save()


class MarkPaidDialog(ctk.CTkToplevel):
    def __init__(self, parent, payment):
        super().__init__(parent)
        self.configure(fg_color="#262c40")
        self.cancelled = False
        self.payment_type = ""
        self.payment_description = ""
        self.title("Mark as Paid")
        self.geometry("460x310")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui(payment)

    def _build_ui(self, payment):
        label(self, "Mark as Paid", bold=True, size=15, fg="#ffffff").pack(pady=(20, 4))
        label(self, f"${payment.amount:,.2f}  —  {payment.description or f'Invoice #{payment.id}'}",
              size=12, fg="#8292a1").pack()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=8)

        section_label(frame, "PAYMENT TYPE").pack(anchor="w", pady=(8, 2))
        self._type_var = ctk.StringVar(value="Check")
        ctk.CTkOptionMenu(
            frame,
            values=["Check", "Cash", "Wire Transfer", "Credit Card", "ACH", "Other"],
            variable=self._type_var,
            width=220,
            fg_color="#1e2d45",
            button_color="#7e67f5",
            button_hover_color="#6952d4",
            dropdown_fg_color="#1a2540",
            text_color="#ffffff",
        ).pack(anchor="w")

        section_label(frame, "PAYMENT DESCRIPTION (optional)").pack(anchor="w", pady=(10, 2))
        self._desc = entry(frame, placeholder="e.g. Check #1042", width=380)
        self._desc.pack(anchor="w")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=16)
        button(btn_row, "Confirm & Generate Receipt", self._submit, width=220,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="left", padx=8)
        button(btn_row, "Cancel", self._cancel, width=100,
               fg_color="gray", hover_color="#555").pack(side="left", padx=8)

    def _submit(self):
        self.payment_type = self._type_var.get()
        self.payment_description = self._desc.get().strip()
        self.destroy()

    def _cancel(self):
        self.cancelled = True
        self.destroy()
