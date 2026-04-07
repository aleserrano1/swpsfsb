"""Reusable CTk widget helpers."""
import customtkinter as ctk


def label(parent, text, bold=False, size=13, fg=None, **kwargs):
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    kw = {"font": font}
    if fg:
        kw["text_color"] = fg
    kw.update(kwargs)
    return ctk.CTkLabel(parent, text=text, **kw)


def entry(parent, placeholder="", width=260, **kwargs):
    return ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, **kwargs)


def button(parent, text, command, width=120, fg_color=None, hover_color=None, **kwargs):
    kw = {"width": width}
    if fg_color:
        kw["fg_color"] = fg_color
    if hover_color:
        kw["hover_color"] = hover_color
    kw.update(kwargs)
    return ctk.CTkButton(parent, text=text, command=command, **kw)


def section_label(parent, text, **kwargs):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="gray",
        **kwargs,
    )


def card_frame(parent, fg_color=None, corner_radius=10, **kwargs):
    kw = {"corner_radius": corner_radius}
    if fg_color:
        kw["fg_color"] = fg_color
    kw.update(kwargs)
    return ctk.CTkFrame(parent, **kw)


def scrollable_frame(parent, **kwargs):
    return ctk.CTkScrollableFrame(parent, **kwargs)


def show_error(title, message):
    import tkinter.messagebox as mb
    mb.showerror(title, message)


def show_info(title, message):
    import tkinter.messagebox as mb
    mb.showinfo(title, message)


def ask_yes_no(title, message) -> bool:
    import tkinter.messagebox as mb
    return mb.askyesno(title, message)
