"""Reusable CTk widget helpers."""
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


def label(parent, text, bold=False, size=13, fg=None, **kwargs):
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    kw = {"font": font}
    if fg:
        kw["text_color"] = fg
    kw.update(kwargs)
    return ctk.CTkLabel(parent, text=text, **kw)


_ENTRY_STYLE = {
    "fg_color": "#1b2333",
    "border_color": "#7e67f5",
    "border_width": 2,
    "corner_radius": 10,
    "placeholder_text_color": "#8292a1",
}


def entry(parent, placeholder="", width=260, **kwargs):
    kw = {**_ENTRY_STYLE, "placeholder_text": placeholder, "width": width}
    kw.update(kwargs)
    return ctk.CTkEntry(parent, **kw)


def _phone_validate(new_val: str) -> bool:
    return new_val == "" or (new_val.isdigit() and len(new_val) <= 15)


def phone_entry(parent, placeholder="Phone number", width=260, **kwargs):
    """CTkEntry that only accepts digit characters (no letters, symbols, or spaces)."""
    kw = {**_ENTRY_STYLE, "placeholder_text": placeholder, "width": width}
    kw.update(kwargs)
    e = ctk.CTkEntry(parent, **kw)
    vcmd = (e.register(_phone_validate), '%P')
    e.configure(validate='key', validatecommand=vcmd)
    return e


def textbox(parent, width=400, height=80, **kwargs):
    """Themed CTkTextbox matching the app's dark input style."""
    kw = {
        "fg_color": "#1b2333",
        "border_color": "#7e67f5",
        "border_width": 2,
        "corner_radius": 10,
        "text_color": "#ffffff",
        "width": width,
        "height": height,
    }
    kw.update(kwargs)
    return ctk.CTkTextbox(parent, **kw)


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
        text_color="#8292a1",
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


class GradientButton(tk.Canvas):
    """Left-to-right PIL gradient button with rounded corners and hover state.

    Renders a smooth gradient onto a PIL image, applies a rounded-rectangle
    mask, then displays it on a tk.Canvas so CTkButton limitations are bypassed.
    The *parent_bg* must match the actual rendered background behind the widget
    so the masked corners blend seamlessly.
    """

    def __init__(self, parent, text, command,
                 colors=("#A08DFF", "#7E67F5"),
                 parent_bg="#262c40",
                 width=150, height=36, corner_radius=18,
                 font_size=13):
        super().__init__(
            parent, width=width, height=height,
            bg=parent_bg, highlightthickness=0, bd=0, cursor="hand2",
        )
        self._command = command
        self._colors = colors
        self._parent_bg = parent_bg
        # NOTE: _w is reserved by tkinter (Tcl widget path) — use _btn_* prefix
        self._btn_w = width
        self._btn_h = height
        self._btn_cr = corner_radius

        # Keep PIL image refs alive to prevent garbage collection
        self._pil_normal = self._render(1.0)
        self._pil_hover  = self._render(0.85)
        self._photo_normal = ImageTk.PhotoImage(self._pil_normal, master=self)
        self._photo_hover  = ImageTk.PhotoImage(self._pil_hover,  master=self)

        self._img_id  = self.create_image(0, 0, anchor="nw", image=self._photo_normal)
        self._text_id = self.create_text(
            width // 2, height // 2, text=text,
            fill="white", font=("Segoe UI", font_size, "bold"),
        )

        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    self._hover_on)
        self.bind("<Leave>",    self._hover_off)

    def _parse(self, hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _render(self, brightness: float) -> Image.Image:
        w, h, cr = self._btn_w, self._btn_h, self._btn_cr
        r1, g1, b1 = self._parse(self._colors[0])
        r2, g2, b2 = self._parse(self._colors[1])
        pb = self._parse(self._parent_bg)

        # Base filled with parent background (corners will show this)
        base = Image.new("RGB", (w, h), pb)

        # Gradient strip covering the full rectangle
        grad = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(grad)
        for x in range(w):
            t = x / max(w - 1, 1)
            r = min(255, int((r1 + (r2 - r1) * t) * brightness))
            g = min(255, int((g1 + (g2 - g1) * t) * brightness))
            b = min(255, int((b1 + (b2 - b1) * t) * brightness))
            draw.line([(x, 0), (x, h - 1)], fill=(r, g, b))

        # Rounded-rectangle mask — white = show gradient, black = show parent bg
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=cr, fill=255)
        base.paste(grad, mask=mask)
        return base

    def _click(self, _event=None):
        if self._command:
            self._command()

    def _hover_on(self, _event=None):
        self.itemconfig(self._img_id, image=self._photo_hover)

    def _hover_off(self, _event=None):
        self.itemconfig(self._img_id, image=self._photo_normal)


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

        self._entry = ctk.CTkEntry(
            self, placeholder_text=placeholder, width=width,
            **_ENTRY_STYLE,
        )
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
            bg="#1b2333",
            fg="white",
            selectbackground="#7e67f5",
            selectforeground="white",
            borderwidth=1,
            relief="solid",
            highlightthickness=1,
            highlightcolor="#7e67f5",
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
