"""Dialog to generate a quote PDF (not saved to DB)."""
import os
from datetime import datetime
import customtkinter as ctk

import config
from models.project import get_by_id, get_financials
from models.client import clients_for_project
from models.settings import get_company_info
from models.service import services_for_project
from pdf.proposal import generate as generate_proposal
from ui.widgets import label, entry, button, section_label, show_error, show_info


class QuoteFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int, on_done=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.on_done = on_done
        self.title("Generate Quote")
        self.geometry("480x440")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        label(self, "Generate Quote", bold=True, size=16).pack(pady=(20, 4))
        label(self, "Quote is not stored in the database.", size=11, fg="gray").pack()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=8)

        section_label(scroll, "GENERAL DESCRIPTION (optional)").pack(anchor="w", pady=(8, 2))
        self._desc = ctk.CTkTextbox(scroll, width=400, height=80, corner_radius=8)
        self._desc.pack(anchor="w")

        section_label(scroll, "NOTE (optional)").pack(anchor="w", pady=(10, 2))
        self._note = ctk.CTkTextbox(scroll, width=400, height=80, corner_radius=8)
        self._note.pack(anchor="w")

        button(scroll, "Generate & Save Quote", self._generate, width=220,
               fg_color="#4a90d9", hover_color="#2c6faf").pack(pady=20)

    def _generate(self):
        desc = self._desc.get("1.0", "end").strip()
        note = self._note.get("1.0", "end").strip()

        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        project = get_by_id(self.project_db_id)
        if not project or not base:
            show_error("Error", "Project or output directory not found.")
            return

        folder = os.path.join(base, project.project_id)
        os.makedirs(folder, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"QUOTE-{project.project_id}-{ts}.pdf"
        path = os.path.join(folder, filename)

        clients = clients_for_project(self.project_db_id)
        financials = get_financials(self.project_db_id)
        company_info = get_company_info(project.company)
        services = services_for_project(self.project_db_id)

        # Temporarily attach description/note for PDF generation
        project.proposal_description = desc
        project.proposal_note = note

        try:
            generate_proposal(path, project, clients, services, financials,
                              company_info, is_quote=True)
            show_info("Quote Saved", f"Quote saved:\n{filename}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate quote:\n{e}")
            return

        if self.on_done:
            self.on_done()
        self.destroy()
