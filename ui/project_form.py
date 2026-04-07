"""Create new project form."""
import customtkinter as ctk

from models.project import create as create_project
from models.client import add_client
from ui.theme import COLOR_THEMES, COMPANY_LABELS
from ui.widgets import label, entry, button, section_label, show_error


class ProjectFormScreen(ctk.CTkFrame):
    def __init__(self, parent, on_save, on_cancel, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_save = on_save
        self.on_cancel = on_cancel
        self._client_frames = []
        self._build_ui()

    def _build_ui(self):
        # Header
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=32, pady=(24, 4))
        label(top, "New Project", bold=True, size=22).pack(side="left")
        button(top, "Cancel", self.on_cancel, width=90,
               fg_color="gray", hover_color="#555").pack(side="right")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=32, pady=8)
        self._scroll = scroll

        # Company
        section_label(scroll, "COMPANY").pack(anchor="w", pady=(8, 2))
        self._company_var = ctk.StringVar(value="sfsb")
        company_row = ctk.CTkFrame(scroll, fg_color="transparent")
        company_row.pack(anchor="w", pady=(0, 8))
        for code, name in COMPANY_LABELS.items():
            ctk.CTkRadioButton(
                company_row, text=name,
                variable=self._company_var, value=code,
            ).pack(side="left", padx=(0, 20))

        # Job Site
        section_label(scroll, "JOB SITE").pack(anchor="w", pady=(4, 2))
        self._job_site = entry(scroll, placeholder="Job site address", width=400)
        self._job_site.pack(anchor="w", pady=(0, 8))

        # Tax rate
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(anchor="w", pady=(4, 8))
        section_label(row, "TAX RATE (%)").pack(anchor="w")
        self._tax_rate = entry(row, placeholder="e.g. 8.5", width=120)
        self._tax_rate.pack(anchor="w")

        # Color theme
        section_label(scroll, "COLOR THEME").pack(anchor="w", pady=(8, 4))
        self._color_var = ctk.StringVar(value="blue")
        color_row = ctk.CTkFrame(scroll, fg_color="transparent")
        color_row.pack(anchor="w", pady=(0, 12))
        for name, meta in COLOR_THEMES.items():
            swatch = ctk.CTkFrame(
                color_row, width=28, height=28,
                corner_radius=14, fg_color=meta["hex"],
                cursor="hand2",
            )
            swatch.pack(side="left", padx=3)
            swatch.bind("<Button-1>", lambda e, n=name: self._select_color(n))
            swatch._color_name = name
        self._swatches = color_row
        self._selected_swatch_indicator = label(scroll, "Selected: blue", size=11, fg="gray")
        self._selected_swatch_indicator.pack(anchor="w", pady=(0, 8))

        # Clients
        section_label(scroll, "CLIENTS").pack(anchor="w", pady=(8, 4))
        self._clients_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._clients_frame.pack(fill="x")

        self._add_client_block()
        button(scroll, "+ Add Another Client", self._add_client_block,
               width=200, fg_color="#555", hover_color="#333").pack(anchor="w", pady=(8, 4))

        # Save button
        button(scroll, "Create Project", self._save, width=180,
               fg_color="#4caf50", hover_color="#2e7d32").pack(anchor="w", pady=(16, 8))

    def _select_color(self, name: str):
        self._color_var.set(name)
        self._selected_swatch_indicator.configure(text=f"Selected: {name}")

    def _add_client_block(self):
        idx = len(self._client_frames) + 1
        block = ClientBlock(self._clients_frame, idx, on_remove=self._remove_client_block)
        block.pack(fill="x", pady=4)
        self._client_frames.append(block)

    def _remove_client_block(self, block):
        if len(self._client_frames) <= 1:
            show_error("Cannot Remove", "At least one client is required.")
            return
        self._client_frames.remove(block)
        block.destroy()

    def _save(self):
        # Validate
        tax_str = self._tax_rate.get().strip()
        try:
            tax = float(tax_str) if tax_str else 0.0
        except ValueError:
            show_error("Invalid Input", "Tax rate must be a number.")
            return

        # Validate at least one client with at least one name
        all_client_data = [f.get_data() for f in self._client_frames]
        for cd in all_client_data:
            if not any(n.strip() for n in cd["names"]):
                show_error("Missing Client Name", "Each client must have at least one name.")
                return

        proj = create_project(
            company=self._company_var.get(),
            job_site=self._job_site.get().strip(),
            tax_rate=tax,
            color_theme=self._color_var.get(),
        )

        import config, os
        cfg = config.load()
        base = cfg.get("base_output_dir", "")
        if base:
            folder = os.path.join(base, proj.project_id)
            os.makedirs(folder, exist_ok=True)

        for cd in all_client_data:
            add_client(proj.id, cd["names"], cd["emails"], cd["phones"], cd["addresses"])

        # Defer navigation so this widget is fully done before being destroyed
        proj_id = proj.id
        self.after(0, lambda: self.on_save(proj_id))


class ClientBlock(ctk.CTkFrame):
    def __init__(self, parent, index: int, on_remove, **kwargs):
        super().__init__(parent, corner_radius=8, **kwargs)
        self._on_remove = on_remove
        self._index = index
        self._field_rows = {"names": [], "emails": [], "phones": [], "addresses": []}
        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 0))
        label(header, f"Client {self._index}", bold=True, size=13).pack(side="left")
        button(header, "Remove", lambda: self._on_remove(self),
               width=80, fg_color="#e53935", hover_color="#b71c1c",
               height=26).pack(side="right")

        self._fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._fields_frame.pack(fill="x", padx=12, pady=(4, 8))

        for field_key, label_text, placeholder in [
            ("names",     "Names",     "Full name"),
            ("emails",    "Emails",    "Email address"),
            ("phones",    "Phones",    "Phone number"),
            ("addresses", "Addresses", "Street address"),
        ]:
            self._build_multi_field(field_key, label_text, placeholder)

    def _build_multi_field(self, key: str, label_text: str, placeholder: str):
        row_container = ctk.CTkFrame(self._fields_frame, fg_color="transparent")
        row_container.pack(fill="x", pady=2)

        header_row = ctk.CTkFrame(row_container, fg_color="transparent")
        header_row.pack(fill="x")
        section_label(header_row, label_text.upper()).pack(side="left")
        button(header_row, f"+ {label_text}", lambda k=key, p=placeholder, rc=row_container: self._add_field(k, p, rc),
               width=100, height=22, fg_color="#555", hover_color="#333").pack(side="left", padx=8)

        entries_frame = ctk.CTkFrame(row_container, fg_color="transparent")
        entries_frame.pack(fill="x")

        # Start with one entry
        e = entry(entries_frame, placeholder=placeholder, width=300)
        e.pack(anchor="w", pady=1)
        self._field_rows[key].append((entries_frame, e))

    def _add_field(self, key: str, placeholder: str, row_container):
        # Find the entries_frame (second child of row_container)
        children = row_container.winfo_children()
        entries_frame = children[-1]
        e = entry(entries_frame, placeholder=placeholder, width=300)
        e.pack(anchor="w", pady=1)
        self._field_rows[key].append((entries_frame, e))

    def get_data(self) -> dict:
        result = {}
        for key, rows in self._field_rows.items():
            result[key] = [e.get() for _, e in rows]
        return result
