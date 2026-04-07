"""Startup screen: connect to existing DB or create new one."""
import os
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk

import config
from database import connection as db
from database.schema import initialize
from models.settings import set_pin, pin_is_set
from ui.widgets import label, button, show_error


class StartupWindow(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title("Construction Manager — Setup")
        self.geometry("460x340")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.master.destroy()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Construction Project Manager",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(36, 6))
        ctk.CTkLabel(
            self, text="Choose how to connect to a database.",
            text_color="gray", font=ctk.CTkFont(size=13),
        ).pack(pady=(0, 28))

        button(self, "Connect to Existing Database", self._connect_existing,
               width=280, height=42).pack(pady=8)
        button(self, "Create New Database", self._create_new,
               width=280, height=42,
               fg_color="#4caf50", hover_color="#2e7d32").pack(pady=8)

    def _connect_existing(self):
        path = fd.askopenfilename(
            title="Select Database File",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if not path:
            return
        self._open_db(path)

    def _create_new(self):
        path = fd.asksaveasfilename(
            title="Create New Database",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
        )
        if not path:
            return

        # Ask for base output directory
        base_dir = fd.askdirectory(title="Select Base Output Directory for Project Files")
        if not base_dir:
            return

        # Ask for PIN
        pin = self._ask_pin()
        if pin is None:
            return

        db.set_path(path)
        try:
            initialize()
            set_pin(pin)
            cfg = config.load()
            cfg["db_path"] = path
            cfg["base_output_dir"] = base_dir
            config.save(cfg)
            self.destroy()
            self.on_success()
        except Exception as e:
            show_error("Error", f"Failed to create database:\n{e}")

    def _open_db(self, path: str):
        if not os.path.exists(path):
            show_error("Error", "File not found.")
            return
        db.set_path(path)
        try:
            initialize()
            cfg = config.load()
            cfg["db_path"] = path
            config.save(cfg)
            self.destroy()
            self.on_success()
        except Exception as e:
            show_error("Error", f"Failed to open database:\n{e}")

    def _ask_pin(self) -> str | None:
        dialog = PinSetupDialog(self)
        self.wait_window(dialog)
        return dialog.result


class PinSetupDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("Set PIN")
        self.geometry("320x240")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        label(self, "Set a 4-digit PIN", bold=True, size=15).pack(pady=(24, 4))
        label(self, "This PIN protects proposal re-generation.", size=11, fg="gray").pack(pady=(0, 16))

        self._pin1 = ctk.CTkEntry(self, placeholder_text="Enter PIN", show="*", width=180)
        self._pin1.pack(pady=4)
        self._pin2 = ctk.CTkEntry(self, placeholder_text="Confirm PIN", show="*", width=180)
        self._pin2.pack(pady=4)

        button(self, "Set PIN", self._submit, width=140).pack(pady=16)

    def _submit(self):
        p1 = self._pin1.get().strip()
        p2 = self._pin2.get().strip()
        if not p1.isdigit() or len(p1) != 4:
            show_error("Invalid PIN", "PIN must be exactly 4 digits.")
            return
        if p1 != p2:
            show_error("Mismatch", "PINs do not match.")
            return
        self.result = p1
        self.destroy()


class PinEntryDialog(ctk.CTkToplevel):
    """Prompt the user to enter the current PIN. Returns the entered value."""
    def __init__(self, parent, prompt="Enter PIN to continue:"):
        super().__init__(parent)
        self.result = None
        self.title("PIN Required")
        self.geometry("300x200")
        self.resizable(False, False)
        self.grab_set()
        self._prompt = prompt
        self._build_ui()

    def _build_ui(self):
        label(self, self._prompt, bold=False, size=12).pack(pady=(28, 8))
        self._pin = ctk.CTkEntry(self, placeholder_text="4-digit PIN", show="*", width=160)
        self._pin.pack(pady=4)
        button(self, "OK", self._submit, width=100).pack(pady=12)

    def _submit(self):
        self.result = self._pin.get().strip()
        self.destroy()
