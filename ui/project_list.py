"""Project list with search and color-accented cards."""
import customtkinter as ctk

from models.project import all_projects, search
from models.client import clients_for_project
from ui.theme import COLOR_THEMES, COMPANY_LABELS, STATUS_LABELS, STATUS_COLORS
from ui.widgets import label, button, scrollable_frame


class ProjectListScreen(ctk.CTkFrame):
    def __init__(self, parent, on_open_project, on_new_project, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_open_project = on_open_project
        self.on_new_project = on_new_project
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=32, pady=(24, 8))

        label(top, "Projects", bold=True, size=22).pack(side="left")
        button(top, "+ New Project", self.on_new_project, width=140,
               fg_color="#4caf50", hover_color="#2e7d32").pack(side="right")

        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=32, pady=(0, 12))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by project ID, client name, or job site...",
            textvariable=self._search_var,
            width=420, height=36,
        )
        self._search_entry.pack(side="left")

        # Scrollable card list
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=32, pady=(0, 16))

    def _on_search(self, *_):
        term = self._search_var.get().strip()
        if term:
            projects = search(term)
        else:
            projects = all_projects()
        self._render_cards(projects)

    def refresh(self):
        projects = all_projects()
        self._render_cards(projects)

    def _render_cards(self, projects):
        for widget in self._scroll.winfo_children():
            widget.destroy()

        if not projects:
            label(self._scroll, "No projects found.", fg="gray", size=13).pack(pady=40)
            return

        for proj in projects:
            self._make_card(proj)

    def _make_card(self, proj):
        color = COLOR_THEMES.get(proj.color_theme, COLOR_THEMES["blue"])
        accent = color["hex"]
        dark_accent = color["dark"]

        card = ctk.CTkFrame(self._scroll, corner_radius=10, fg_color=("white", "#2b2b2b"))
        card.pack(fill="x", pady=5)
        card.bind("<Button-1>", lambda e, p=proj: self.on_open_project(p.id))

        # Left accent bar
        bar = ctk.CTkFrame(card, width=6, corner_radius=0,
                           fg_color=accent)
        bar.pack(side="left", fill="y")
        bar.bind("<Button-1>", lambda e, p=proj: self.on_open_project(p.id))

        # Content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        content.bind("<Button-1>", lambda e, p=proj: self.on_open_project(p.id))

        # Row 1: project ID + company
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")
        label(row1, proj.project_id, bold=True, size=14).pack(side="left")

        company_badge = ctk.CTkLabel(
            row1,
            text=COMPANY_LABELS.get(proj.company, proj.company),
            font=ctk.CTkFont(size=10),
            fg_color=accent,
            text_color="white",
            corner_radius=6,
            padx=8, pady=2,
        )
        company_badge.pack(side="left", padx=(10, 0))

        status_color = STATUS_COLORS.get(proj.status, "#888")
        status_badge = ctk.CTkLabel(
            row1,
            text=STATUS_LABELS.get(proj.status, proj.status),
            font=ctk.CTkFont(size=10),
            fg_color=status_color,
            text_color="white",
            corner_radius=6,
            padx=8, pady=2,
        )
        status_badge.pack(side="left", padx=(6, 0))

        # Row 2: client names
        clients = clients_for_project(proj.id)
        client_names = []
        for c in clients:
            client_names.extend(c.names)
        client_str = ", ".join(client_names) if client_names else "No client"
        label(content, client_str, size=12, fg="gray").pack(anchor="w", pady=(2, 0))

        # Row 3: job site
        if proj.job_site:
            label(content, f"Job Site: {proj.job_site}", size=11, fg="gray").pack(anchor="w")

        # Click area
        for widget in [content, row1]:
            widget.bind("<Button-1>", lambda e, p=proj: self.on_open_project(p.id))
