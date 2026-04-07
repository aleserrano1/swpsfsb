"""Main application window with sidebar navigation."""
import customtkinter as ctk

from ui.project_list import ProjectListScreen
from ui.project_form import ProjectFormScreen
from ui.project_detail import ProjectDetailScreen
from ui.settings_screen import SettingsScreen


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Construction Project Manager")
        self.geometry("1100x720")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_layout()
        self._show_projects()

    def _build_layout(self):
        # ── Sidebar ──────────────────────────────────────────────────────────
        self._sidebar = ctk.CTkFrame(self, width=190, corner_radius=0,
                                     fg_color=("gray85", "#1a1a2e"))
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self._sidebar,
            text="SWPSFSB",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("gray20", "#4a90d9"),
        ).pack(pady=(28, 24))

        self._nav_buttons = {}
        for name, text, cmd in [
            ("projects", "Projects", self._show_projects),
            ("settings", "Settings", self._show_settings),
        ]:
            btn = ctk.CTkButton(
                self._sidebar, text=text, command=cmd,
                anchor="w", fg_color="transparent",
                hover_color=("gray75", "#2b2b4e"),
                text_color=("gray20", "white"),
                height=38, corner_radius=8,
                font=ctk.CTkFont(size=13),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[name] = btn

        # ── Content area ─────────────────────────────────────────────────────
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)

    def _clear_content(self):
        for widget in self._content.winfo_children():
            widget.destroy()

    def _set_active_nav(self, name: str):
        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=("gray75", "#2b2b4e"))
            else:
                btn.configure(fg_color="transparent")

    def _show_projects(self):
        self._clear_content()
        self._set_active_nav("projects")
        screen = ProjectListScreen(
            self._content,
            on_open_project=self._open_project,
            on_new_project=self._new_project,
        )
        screen.pack(fill="both", expand=True)
        self._project_list_screen = screen

    def _new_project(self):
        self._clear_content()
        ProjectFormScreen(
            self._content,
            on_save=self._on_project_created,
            on_cancel=self._show_projects,
        ).pack(fill="both", expand=True)

    def _on_project_created(self, project_db_id: int):
        self._open_project(project_db_id)

    def _open_project(self, project_db_id: int):
        self._clear_content()
        ProjectDetailScreen(
            self._content,
            project_db_id=project_db_id,
            on_back=self._show_projects,
        ).pack(fill="both", expand=True)

    def _show_settings(self):
        self._clear_content()
        self._set_active_nav("settings")
        SettingsScreen(self._content).pack(fill="both", expand=True)
