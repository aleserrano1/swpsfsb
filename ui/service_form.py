"""Dialog to add a service or change order."""
import customtkinter as ctk

from models.service import add_service, add_subfield
from ui.widgets import label, entry, button, section_label, textbox, show_error


class ServiceFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int,
                 service_type: str = "original_service", on_save=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.service_type = service_type
        self.on_save = on_save
        self._subfield_entries = []  # list of CTkEntry widgets

        title_map = {
            "original_service": "Add Service",
            "order_change": "Add Change Order",
        }
        self._title_text = title_map.get(service_type, "Add Service")
        self.title(self._title_text)
        self.geometry("460x560")
        self.resizable(False, True)
        self.grab_set()
        self.configure(fg_color="#262c40")
        self._build_ui()

    def _build_ui(self):
        label(self, self._title_text, bold=True, size=16, fg="#ffffff").pack(pady=(20, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        def make_card(parent):
            card = ctk.CTkFrame(parent, fg_color="#0d1826", corner_radius=16)
            card.pack(fill="x", pady=(0, 12))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=14)
            return inner

        # Description card
        desc_inner = make_card(scroll)
        section_label(desc_inner, "DESCRIPTION").pack(anchor="w", pady=(0, 6))
        self._desc = textbox(desc_inner, width=370, height=80)
        self._desc.pack(anchor="w")

        # Amount card
        amt_inner = make_card(scroll)
        section_label(amt_inner, "AMOUNT ($)").pack(anchor="w", pady=(0, 6))
        self._amount = entry(amt_inner, placeholder="e.g. 1500.00", width=200)
        self._amount.pack(anchor="w")

        # Subfields card
        sub_card = ctk.CTkFrame(scroll, fg_color="#0d1826", corner_radius=16)
        sub_card.pack(fill="x", pady=(0, 12))
        sub_inner = ctk.CTkFrame(sub_card, fg_color="transparent")
        sub_inner.pack(fill="x", padx=16, pady=14)

        subfields_header = ctk.CTkFrame(sub_inner, fg_color="transparent")
        subfields_header.pack(fill="x", pady=(0, 8))
        section_label(subfields_header, "SUBFIELDS (optional)").pack(side="left")
        button(subfields_header, "+ Add", self._add_subfield_row,
               width=70, height=24).pack(side="right")

        self._subfields_container = ctk.CTkScrollableFrame(
            sub_inner, height=120, corner_radius=8, fg_color="#15233a"
        )
        self._subfields_container.pack(fill="x")

        button(scroll, "Save", self._save, width=140,
               fg_color="#4caf50", hover_color="#2e7d32").pack(pady=(4, 16))

    def _add_subfield_row(self, text=""):
        row = ctk.CTkFrame(self._subfields_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        e = ctk.CTkEntry(
            row, placeholder_text="Describe detail...",
            corner_radius=10, fg_color="#1b2333", border_color="#7e67f5",
            border_width=2, placeholder_text_color="#8292a1",
        )
        e.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if text:
            e.insert(0, text)

        def _remove(r=row, en=e):
            self._subfield_entries.remove(en)
            r.destroy()

        ctk.CTkButton(row, text="×", width=28, height=28,
                      fg_color="#e53935", hover_color="#b71c1c",
                      command=_remove).pack(side="right")

        self._subfield_entries.append(e)

    def _save(self):
        desc = self._desc.get("1.0", "end").strip()
        amt_str = self._amount.get().strip()
        if not desc:
            show_error("Missing Description", "Please enter a description.")
            return
        try:
            amt = float(amt_str)
        except ValueError:
            show_error("Invalid Amount", "Please enter a valid number.")
            return

        subfield_texts = [e.get().strip() for e in self._subfield_entries
                          if e.get().strip()]

        try:
            svc = add_service(self.project_db_id, desc, amt, self.service_type)
        except ValueError as e:
            show_error("Not Allowed", str(e))
            return

        for i, text in enumerate(subfield_texts):
            add_subfield(svc.id, text, sort_order=i)

        if self.on_save:
            self.on_save()
        self.destroy()
