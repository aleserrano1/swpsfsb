"""Reusable CTk widget helpers."""
import tkinter as tk
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


def _phone_validate(new_val: str) -> bool:
    return new_val == "" or (new_val.isdigit() and len(new_val) <= 15)


def phone_entry(parent, placeholder="Phone number", width=260, **kwargs):
    """CTkEntry that only accepts digit characters (no letters, symbols, or spaces)."""
    e = ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, **kwargs)
    vcmd = (e.register(_phone_validate), '%P')
    e.configure(validate='key', validatecommand=vcmd)
    return e


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


class AutocompleteEntry(ctk.CTkFrame):
    """CTkEntry with a dropdown suggestion popup backed by a search function.

    Compatible with CTkEntry: exposes get(), insert(), delete(), configure().
    For phone fields pass phone_mode=True to restrict input to digits only.
    """

    def __init__(self, parent, search_fn, placeholder="", width=260,
                 phone_mode=False, **kwargs):
        super().__init__(parent, fg_color="transparent", corner_radius=0, **kwargs)
        self._search_fn = search_fn
        self._phone_mode = phone_mode
        self._popup = None
        self._listbox = None
        self._after_id = None

        self._entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=width)
        if phone_mode:
            vcmd = (self._entry.register(_phone_validate), "%P")
            self._entry.configure(validate="key", validatecommand=vcmd)
        self._entry.pack(fill="both", expand=True)

        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Escape>", lambda e: self._close_popup())
        self._entry.bind("<Down>", self._on_arrow_down)
        self.bind("<Destroy>", lambda e: self._close_popup())

    # ---- Public CTkEntry-compatible interface ----

    def get(self) -> str:
        return self._entry.get()

    def insert(self, index, string: str):
        self._entry.insert(index, string)

    def delete(self, first, last="end"):
        self._entry.delete(first, last)

    def configure(self, **kwargs):
        self._entry.configure(**kwargs)

    def focus_set(self):
        self._entry.focus_set()

    # ---- Autocomplete logic ----

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(250, self._do_search)

    def _do_search(self):
        q = self._entry.get().strip()
        if not q:
            self._close_popup()
            return
        try:
            results = self._search_fn(q)
        except Exception:
            return
        if results:
            self._show_popup(results)
        else:
            self._close_popup()

    def _show_popup(self, results):
        self._close_popup()
        try:
            x = self._entry.winfo_rootx()
            y = self._entry.winfo_rooty() + self._entry.winfo_height()
            w = max(self._entry.winfo_width(), 160)
        except Exception:
            return

        row_h = 26
        visible = min(len(results), 7)
        h = row_h * visible + 2

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_attributes("-topmost", True)
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

        self._listbox = tk.Listbox(
            self._popup,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#4a90d9",
            selectforeground="white",
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
            font=("Segoe UI", 11),
            activestyle="none",
        )
        self._listbox.pack(fill="both", expand=True)

        for r in results:
            self._listbox.insert("end", r)

        # Use Button-1 (press) so selection fires before FocusOut closes popup
        self._listbox.bind("<Button-1>", self._on_listbox_press)
        self._listbox.bind("<Return>", self._on_listbox_keyboard_select)
        self._listbox.bind("<Escape>", lambda e: self._close_popup())
        self._listbox.bind("<Up>", self._on_listbox_up)

    def _on_listbox_press(self, event):
        idx = self._listbox.nearest(event.y)
        if 0 <= idx < self._listbox.size():
            value = self._listbox.get(idx)
            self._entry.delete(0, "end")
            self._entry.insert(0, value)
        self._close_popup()
        self._entry.focus_set()

    def _on_listbox_keyboard_select(self, event=None):
        if not self._listbox:
            return
        sel = self._listbox.curselection()
        if sel:
            value = self._listbox.get(sel[0])
            self._entry.delete(0, "end")
            self._entry.insert(0, value)
        self._close_popup()
        self._entry.focus_set()

    def _on_focus_out(self, event):
        # Delay so a listbox Button-1 press can fire and close popup first
        self.after(200, self._close_popup)

    def _close_popup(self, event=None):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
            self._listbox = None

    def _on_arrow_down(self, event):
        if self._listbox and self._listbox.size() > 0:
            self._listbox.focus_set()
            self._listbox.selection_clear(0, "end")
            self._listbox.selection_set(0)
            self._listbox.activate(0)

    def _on_listbox_up(self, event):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel and sel[0] == 0:
                self._entry.focus_set()
