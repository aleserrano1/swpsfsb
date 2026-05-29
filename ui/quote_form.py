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
from ui.widgets import label, entry, button, section_label, textbox, show_error, show_info


class QuoteFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, project_db_id: int, on_done=None):
        super().__init__(parent)
        self.project_db_id = project_db_id
        self.on_done = on_done
        self.title("Generate Quote")
        self.geometry("500x500")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color="#262c40")
        self._build_ui()

    def _build_ui(self):
        label(self, "Generate Quote", bold=True, size=16, fg="#ffffff").pack(pady=(20, 4))
        label(self, "Quote is not stored in the database.", size=11, fg="#8292a1").pack(pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        def make_card(parent):
            card = ctk.CTkFrame(parent, fg_color="#0d1826", corner_radius=16)
            card.pack(fill="x", pady=(0, 12))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=14)
            return inner

        # General Description card
        desc_inner = make_card(scroll)
        section_label(desc_inner, "GENERAL DESCRIPTION (optional)").pack(anchor="w", pady=(0, 6))
        self._desc = textbox(desc_inner, width=420, height=80)
        self._desc.pack(anchor="w")

        # Note card
        note_inner = make_card(scroll)
        section_label(note_inner, "NOTE (optional)").pack(anchor="w", pady=(0, 6))
        self._note = textbox(note_inner, width=420, height=80)
        self._note.pack(anchor="w")

        button(scroll, "Generate & Save Quote", self._generate, width=220,
               fg_color="#4a90d9", hover_color="#2c6faf").pack(pady=(4, 16))

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
        services = [s for s in services_for_project(self.project_db_id) if not s.is_hidden]

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
