"""Settings screen: company info, PIN change, base output directory."""
import tkinter.filedialog as fd
import customtkinter as ctk

import config
from models.settings import get, set_value, verify_pin, set_pin
from ui.widgets import label, entry, button, section_label, show_error, show_info
from ui.startup import PinEntryDialog


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        label(self, "Settings", bold=True, size=22).pack(anchor="w", padx=32, pady=(24, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=32, pady=8)

        self._fields = {}
        for company, cname in [("sfsb", "Santa Fe Style Builders"), ("swp", "Southwest Plastering Co.")]:
            self._build_company_section(scroll, company, cname)

        self._build_directory_section(scroll)
        self._build_pin_section(scroll)

        button(scroll, "Save Settings", self._save, width=160,
               fg_color="#4caf50", hover_color="#2e7d32").pack(anchor="w", pady=(20, 8))

    def _build_company_section(self, parent, company: str, name: str):
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.pack(fill="x", pady=8)

        label(frame, name, bold=True, size=14).pack(anchor="w", padx=16, pady=(12, 4))

        for field_key, placeholder in [
            (f"{company}_president", "President Name"),
            (f"{company}_address", "Company Address"),
            (f"{company}_phone", "Phone Number"),
        ]:
            section_label(frame, placeholder.upper()).pack(anchor="w", padx=16, pady=(4, 0))
            e = entry(frame, placeholder=placeholder, width=380)
            e.pack(anchor="w", padx=16, pady=(0, 4))
            e.insert(0, get(field_key))
            self._fields[field_key] = e

        ctk.CTkFrame(frame, height=12, fg_color="transparent").pack()

    def _build_directory_section(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.pack(fill="x", pady=8)
        label(frame, "Output Directory", bold=True, size=14).pack(anchor="w", padx=16, pady=(12, 4))
        section_label(frame, "BASE FOLDER FOR PROJECT FILES").pack(anchor="w", padx=16, pady=(4, 0))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=(0, 12))

        cfg = config.load()
        self._dir_entry = entry(row, placeholder="Select directory...", width=320)
        self._dir_entry.pack(side="left", padx=(0, 8))
        self._dir_entry.insert(0, cfg.get("base_output_dir", ""))
        button(row, "Browse", self._browse_dir, width=80).pack(side="left")

    def _browse_dir(self):
        d = fd.askdirectory(title="Select Base Output Directory")
        if d:
            self._dir_entry.delete(0, "end")
            self._dir_entry.insert(0, d)

    def _build_pin_section(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.pack(fill="x", pady=8)
        label(frame, "Security", bold=True, size=14).pack(anchor="w", padx=16, pady=(12, 4))
        button(frame, "Change PIN", self._change_pin, width=140).pack(anchor="w", padx=16, pady=(4, 12))

    def _change_pin(self):
        old_dialog = PinEntryDialog(self, "Enter current PIN:")
        self.wait_window(old_dialog)
        if old_dialog.result is None:
            return
        if not verify_pin(old_dialog.result):
            show_error("Wrong PIN", "Incorrect PIN entered.")
            return

        from ui.startup import PinSetupDialog
        new_dialog = PinSetupDialog(self)
        self.wait_window(new_dialog)
        if new_dialog.result:
            set_pin(new_dialog.result)
            show_info("PIN Changed", "PIN updated successfully.")

    def _save(self):
        for key, widget in self._fields.items():
            set_value(key, widget.get().strip())

        cfg = config.load()
        cfg["base_output_dir"] = self._dir_entry.get().strip()
        config.save(cfg)
        show_info("Saved", "Settings saved successfully.")
