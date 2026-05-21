"""Project list with search and color-accented cards."""
import os
import tkinter as tk
from datetime import datetime
import customtkinter as ctk

from models.project import all_projects, search, get_financials
from models.client import clients_for_project
from pdf.accounts_receivable import generate as generate_ar
from ui.theme import COLOR_THEMES, COMPANY_LABELS, STATUS_LABELS, STATUS_COLORS
from ui.widgets import label, button, scrollable_frame, show_error, show_info


class _ProgressRing(tk.Canvas):
    """Circular arc progress indicator drawn on a tkinter Canvas."""

    def __init__(self, parent, size=76, percentage=0,
                 track_color="#1c2d40", progress_color="#7e67f5",
                 bg_color="#0d1826", **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        m, stroke = 7, 7
        x0, y0, x1, y1 = m, m, size - m, size - m
        self.create_arc(x0, y0, x1, y1, start=0, extent=359.9,
                        style="arc", outline=track_color, width=stroke)
        if percentage > 0:
            self.create_arc(x0, y0, x1, y1, start=90,
                            extent=-(360 * percentage / 100),
                            style="arc", outline=progress_color, width=stroke)
        self.create_text(size / 2, size / 2, text=f"{percentage}%",
                         fill="white", font=("Segoe UI", 13, "bold"))


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
        button(top, "AR Report", self._generate_ar_report, width=100,
               fg_color="#4a90d9", hover_color="#2c6faf").pack(side="right", padx=(0, 8))

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

    def _generate_ar_report(self):
        import config as cfg

        conf = cfg.load()
        base_dir = conf.get("base_output_dir", "").strip()
        if not base_dir or not os.path.isdir(base_dir):
            show_error("AR Report", "Base output directory is not configured or does not exist.")
            return

        projects = all_projects()
        if not projects:
            show_info("No Projects", "No projects found to include in the report.")
            return

        projects_data = []
        for proj in projects:
            clients = clients_for_project(proj.id)
            client_names = [n for c in clients for n in c.names]
            financials = get_financials(proj.id)
            projects_data.append({
                "project_id": proj.project_id,
                "company":    proj.company,
                "status":     proj.status,
                "created_at": proj.created_at,
                "client_names": client_names,
                "financials": financials,
            })

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"AccountsReceivableReport_{ts}.pdf"
        path = os.path.join(base_dir, filename)

        try:
            generate_ar(path, projects_data)
            show_info("Report Generated",
                      f"Accounts Receivable Report saved:\n{filename}")
        except Exception as e:
            show_error("PDF Error", f"Could not generate report:\n{e}")

    def _make_card(self, proj):
        # Financials for progress ring
        fin = get_financials(proj.id)
        total = fin["total"]
        paid = fin["paid"]
        pct = int(round((paid / total * 100) if total > 0 else 0))
        pct = max(0, min(100, pct))

        # Client names
        clients = clients_for_project(proj.id)
        client_names = []
        for c in clients:
            client_names.extend(c.names)
        client_str = ", ".join(client_names) if client_names else "No client"

        # Job site string (primary text)
        js = proj.job_site
        js_parts = [p for p in [
            js.get("line1"), js.get("line2"),
            ", ".join(filter(None, [js.get("city"), js.get("state")])),
            js.get("zip_code"),
        ] if p]
        job_site_str = ", ".join(js_parts) if js_parts else "No job site"

        # Card
        card = ctk.CTkFrame(self._scroll, corner_radius=16, fg_color="#0d1826")
        card.pack(fill="x", pady=5)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Left text ────────────────────────────────────────────────────────
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        accent = COLOR_THEMES.get(proj.color_theme, COLOR_THEMES["blue"])["hex"]
        badges = ctk.CTkFrame(left, fg_color="transparent")
        badges.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(badges, text=COMPANY_LABELS.get(proj.company, proj.company),
                     font=ctk.CTkFont(size=10), fg_color=accent,
                     text_color="white", corner_radius=6, padx=8, pady=2).pack(side="left")
        ctk.CTkLabel(badges, text=STATUS_LABELS.get(proj.status, proj.status),
                     font=ctk.CTkFont(size=10),
                     fg_color=STATUS_COLORS.get(proj.status, "#888"),
                     text_color="white", corner_radius=6, padx=8, pady=2).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(left, text=job_site_str,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#ffffff", anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text=client_str,
                     font=ctk.CTkFont(size=12), text_color="#8292a1",
                     anchor="w").pack(anchor="w", pady=(3, 0))
        ctk.CTkLabel(left, text=proj.project_id,
                     font=ctk.CTkFont(size=11), text_color="#8292a1",
                     anchor="w").pack(anchor="w", pady=(1, 0))

        # ── Right: progress ring ─────────────────────────────────────────────
        ring = _ProgressRing(inner, size=76, percentage=pct)
        ring.pack(side="right", padx=(16, 0))

        # Click bindings
        def _open(e, p=proj):
            self.on_open_project(p.id)
        for w in [card, inner, left, badges, ring]:
            w.bind("<Button-1>", _open)
