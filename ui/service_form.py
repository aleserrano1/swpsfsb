"""Dialog to add a service or change order."""
import customtkinter as ctk

from models.service import add_service
from ui.widgets import label, entry, button, section_label, show_error


class ServiceFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int,
                 service_type: str = "original_service", on_save=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.service_type = service_type
        self.on_save = on_save

        title_map = {
            "original_service": "Add Service",
            "order_change": "Add Change Order",
        }
        self.title(title_map.get(service_type, "Add Service"))
        self.geometry("400x260")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        label(self, self.title(), bold=True, size=16).pack(pady=(20, 8))

        section_label(self, "DESCRIPTION").pack(anchor="w", padx=24, pady=(4, 2))
        self._desc = ctk.CTkTextbox(self, width=350, height=80, corner_radius=8)
        self._desc.pack(padx=24)

        section_label(self, "AMOUNT ($)").pack(anchor="w", padx=24, pady=(10, 2))
        self._amount = entry(self, placeholder="e.g. 1500.00", width=200)
        self._amount.pack(anchor="w", padx=24)

        button(self, "Save", self._save, width=140,
               fg_color="#4caf50", hover_color="#2e7d32").pack(pady=20)

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

        add_service(self.project_db_id, desc, amt, self.service_type)
        if self.on_save:
            self.on_save()
        self.destroy()
