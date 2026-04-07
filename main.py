"""Entry point for Construction Project Manager."""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk

import config
from database import connection as db
from database.schema import initialize


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.withdraw()  # Hide until startup completes

    cfg = config.load()
    db_path = cfg.get("db_path", "")

    def on_ready():
        root.deiconify()
        from ui.app import App
        # Destroy the hidden root and launch main app
        root.destroy()
        app = App()
        app.mainloop()

    if db_path and os.path.exists(db_path):
        # Auto-connect to last used DB
        try:
            db.set_path(db_path)
            initialize()
            root.destroy()
            from ui.app import App
            app = App()
            app.mainloop()
            return
        except Exception:
            pass  # Fall through to startup screen

    # Show startup screen
    from ui.startup import StartupWindow
    startup = StartupWindow(root, on_success=on_ready)
    root.mainloop()


if __name__ == "__main__":
    main()
