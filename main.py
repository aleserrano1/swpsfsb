"""Entry point for Construction Project Manager."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    from ui.app import App
    App().mainloop()


if __name__ == "__main__":
    main()
