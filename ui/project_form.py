"""Create new project form."""
import customtkinter as ctk

from models.project import create as create_project
from models.client import add_client
from ui.theme import COLOR_THEMES, COMPANY_LABELS
from ui.widgets import label, entry, button, section_label, show_error, phone_entry


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
        job_site_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray25"), corner_radius=6)
        job_site_frame.pack(anchor="w", pady=(0, 8))
        js_inner = ctk.CTkFrame(job_site_frame, fg_color="transparent")
        js_inner.pack(fill="x", padx=8, pady=6)
        self._js_line1 = entry(js_inner, placeholder="Address Line 1 *", width=360)
        self._js_line1.pack(anchor="w", pady=1)
        self._js_line2 = entry(js_inner, placeholder="Address Line 2 (optional)", width=360)
        self._js_line2.pack(anchor="w", pady=1)
        js_city_row = ctk.CTkFrame(js_inner, fg_color="transparent")
        js_city_row.pack(anchor="w", pady=1)
        self._js_city = entry(js_city_row, placeholder="City *", width=190)
        self._js_city.pack(side="left", padx=(0, 6))
        self._js_state = entry(js_city_row, placeholder="State *", width=80)
        self._js_state.pack(side="left", padx=(0, 6))
        self._js_zip = entry(js_city_row, placeholder="Zip Code *", width=110)
        self._js_zip.pack(side="left")

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
        import re

        # Validate tax rate
        tax_str = self._tax_rate.get().strip()
        try:
            tax = float(tax_str) if tax_str else 0.0
        except ValueError:
            show_error("Invalid Input", "Tax rate must be a number.")
            return

        # Validate job site
        js_line1 = self._js_line1.get().strip()
        js_city  = self._js_city.get().strip()
        js_state = self._js_state.get().strip()
        js_zip   = self._js_zip.get().strip()
        if not js_line1:
            show_error("Incomplete Job Site", "Job Site Address Line 1 is required.")
            return
        if not js_city:
            show_error("Incomplete Job Site", "Job Site City is required.")
            return
        if not js_state:
            show_error("Incomplete Job Site", "Job Site State is required.")
            return
        if not js_zip:
            show_error("Incomplete Job Site", "Job Site Zip Code is required.")
            return
        if not re.fullmatch(r"\d{5}(-\d{4})?", js_zip):
            show_error("Invalid Job Site Zip", f"'{js_zip}' is not a valid zip code (e.g. 87501 or 87501-1234).")
            return

        job_site = {
            "line1":    js_line1,
            "line2":    self._js_line2.get().strip(),
            "city":     js_city,
            "state":    js_state,
            "zip_code": js_zip,
        }

        # Validate clients
        all_client_data = [f.get_data() for f in self._client_frames]
        for cd in all_client_data:
            if not any(n.strip() for n in cd["names"]):
                show_error("Missing Client Name", "Each client must have at least one name.")
                return
            for addr in cd["addresses"]:
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
                    show_error("Invalid Zip Code", f"'{zip_val}' is not a valid zip code (e.g. 87501 or 87501-1234).")
                    return

        proj = create_project(
            company=self._company_var.get(),
            job_site=job_site,
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
        self._field_rows = {"names": [], "emails": [], "phones": []}
        self._address_blocks = []  # list of dicts: {line1, line2, city, state, zip_code} -> entry widgets
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
            ("names",  "Names",  "Full name"),
            ("emails", "Emails", "Email address"),
            ("phones", "Phones", "Phone number"),
        ]:
            self._build_multi_field(field_key, label_text, placeholder)

        self._build_address_section()

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

        e = phone_entry(entries_frame, placeholder=placeholder, width=300) if key == "phones" else entry(entries_frame, placeholder=placeholder, width=300)
        e.pack(anchor="w", pady=1)
        self._field_rows[key].append((entries_frame, e))

    def _add_field(self, key: str, placeholder: str, row_container):
        children = row_container.winfo_children()
        entries_frame = children[-1]
        e = phone_entry(entries_frame, placeholder=placeholder, width=300) if key == "phones" else entry(entries_frame, placeholder=placeholder, width=300)
        e.pack(anchor="w", pady=1)
        self._field_rows[key].append((entries_frame, e))

    def _build_address_section(self):
        container = ctk.CTkFrame(self._fields_frame, fg_color="transparent")
        container.pack(fill="x", pady=2)

        header_row = ctk.CTkFrame(container, fg_color="transparent")
        header_row.pack(fill="x")
        section_label(header_row, "ADDRESS").pack(side="left")
        button(header_row, "+ Add Address", lambda: self._add_address_block(),
               width=120, height=22, fg_color="#555", hover_color="#333").pack(side="left", padx=8)

        self._addresses_container = ctk.CTkFrame(container, fg_color="transparent")
        self._addresses_container.pack(fill="x")

        self._add_address_block()

    def _add_address_block(self):
        block = ctk.CTkFrame(self._addresses_container, fg_color=("gray85", "gray25"), corner_radius=6)
        block.pack(fill="x", pady=3)

        inner = ctk.CTkFrame(block, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)

        widgets = {}

        e1 = entry(inner, placeholder="Address Line 1 *", width=340)
        e1.pack(anchor="w", pady=1)
        widgets["line1"] = e1

        e2 = entry(inner, placeholder="Address Line 2 (optional)", width=340)
        e2.pack(anchor="w", pady=1)
        widgets["line2"] = e2

        city_row = ctk.CTkFrame(inner, fg_color="transparent")
        city_row.pack(anchor="w", pady=1)
        e_city = entry(city_row, placeholder="City *", width=190)
        e_city.pack(side="left", padx=(0, 6))
        widgets["city"] = e_city
        e_state = entry(city_row, placeholder="State *", width=80)
        e_state.pack(side="left", padx=(0, 6))
        widgets["state"] = e_state
        e_zip = entry(city_row, placeholder="Zip Code *", width=110)
        e_zip.pack(side="left")
        widgets["zip_code"] = e_zip

        idx = len(self._address_blocks)
        button(inner, "Remove Address",
               lambda b=block, i=idx: self._remove_address_block(b),
               width=130, height=22, fg_color="#e53935", hover_color="#b71c1c").pack(anchor="w", pady=(4, 0))

        self._address_blocks.append({"frame": block, "widgets": widgets})

    def _remove_address_block(self, block_frame):
        self._address_blocks = [b for b in self._address_blocks if b["frame"] is not block_frame]
        block_frame.destroy()

    def get_data(self) -> dict:
        result = {}
        for key, rows in self._field_rows.items():
            result[key] = [e.get() for _, e in rows]

        addresses = []
        for block in self._address_blocks:
            w = block["widgets"]
            addr = {k: w[k].get().strip() for k in w}
            if any(addr.values()):
                addresses.append(addr)
        result["addresses"] = addresses
        return result
