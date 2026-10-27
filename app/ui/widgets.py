"""Reusable widgets: buttons, placeholder entries, tables, logo, modal dialog base."""
import tkinter as tk
from tkinter import ttk

from . import theme
from .theme import BLUE, BLUE_HOVER, BORDER, MUTED, NAVY, RED, RED_HOVER, TEXT, WHITE, font

_BUTTON_KINDS = {
    "primary":   (BLUE, BLUE_HOVER, WHITE),
    "danger":    (RED, RED_HOVER, WHITE),
    "secondary": (WHITE, "#eef2f7", TEXT),
}


def make_button(parent, text, command, kind="primary", padx=18, pady=7, **kw):
    bg, hover, fg = _BUTTON_KINDS[kind]
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=hover,
                    activeforeground=fg, relief="flat", bd=0, cursor="hand2", padx=padx, pady=pady,
                    font=font(10, "bold"), highlightthickness=1 if kind == "secondary" else 0,
                    highlightbackground=BORDER, **kw)
    btn.bind("<Enter>", lambda _e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda _e: btn.config(bg=bg))
    return btn


def draw_logo(parent, size=64, bg=NAVY):
    """The blue rounded-square store icon, drawn with the canvas (no image files needed)."""
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0)
    s, r = size, size * 0.24
    pts = [r, 0, r, 0, s - r, 0, s - r, 0, s, 0, s, r, s, r, s, s - r, s, s - r, s, s, s - r, s,
           s - r, s, r, s, r, s, 0, s, 0, s - r, 0, s - r, 0, r, 0, r, 0, 0]
    c.create_polygon(pts, smooth=True, fill=BLUE, outline=BLUE)
    c.create_rectangle(s * .22, s * .25, s * .78, s * .42, fill=WHITE, outline=WHITE)       # awning
    for i in range(1, 4):
        x = s * (.22 + .56 * i / 4)
        c.create_line(x, s * .25, x, s * .42, fill="#b7cff7")
    c.create_rectangle(s * .27, s * .42, s * .73, s * .74, fill=WHITE, outline=WHITE)       # shop
    c.create_rectangle(s * .44, s * .52, s * .56, s * .74, fill=theme.ORANGE, outline=theme.ORANGE)
    return c


class PlaceholderEntry(tk.Frame):
    """Bordered entry with grey placeholder text and an optional Show/Hide password toggle."""

    def __init__(self, master, placeholder="", password=False, width=30, bg=WHITE):
        super().__init__(master, bg=bg, highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BLUE)
        self.placeholder, self.password = placeholder, password
        self._showing_placeholder, self._revealed = False, False
        self.entry = tk.Entry(self, relief="flat", bd=0, font=font(10), bg=bg, fg=TEXT,
                              insertbackground=TEXT, width=width)
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=9)
        if password:
            self.toggle = tk.Label(self, text="Show", fg=BLUE, bg=bg, cursor="hand2", font=font(9))
            self.toggle.pack(side="right", padx=(0, 10))
            self.toggle.bind("<Button-1>", lambda _e: self._toggle_reveal())
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self._show_placeholder()

    def _mask(self):
        return "" if (not self.password or self._revealed) else "\u2022"

    def _show_placeholder(self):
        if not self.entry.get() and self.placeholder:
            self._showing_placeholder = True
            self.entry.config(show="", fg=MUTED)
            self.entry.insert(0, self.placeholder)

    def _focus_in(self, _e=None):
        self.config(highlightbackground=BLUE)
        if self._showing_placeholder:
            self.entry.delete(0, "end")
            self._showing_placeholder = False
            self.entry.config(fg=TEXT, show=self._mask())

    def _focus_out(self, _e=None):
        self.config(highlightbackground=BORDER)
        if not self.entry.get():
            self._show_placeholder()

    def _toggle_reveal(self):
        self._revealed = not self._revealed
        self.toggle.config(text="Hide" if self._revealed else "Show")
        if not self._showing_placeholder:
            self.entry.config(show=self._mask())

    def get(self):
        return "" if self._showing_placeholder else self.entry.get()

    def set(self, text):
        self._focus_in()
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.config(fg=TEXT, show=self._mask())
        self._showing_placeholder = False

    def clear(self):
        self.entry.delete(0, "end")
        self._showing_placeholder = False
        self.entry.config(fg=TEXT, show=self._mask())
        try:
            focused = self.focus_get()
        except KeyError:                      # Tk quirk when a combobox popdown has focus
            focused = None
        if focused is not self.entry:
            self._show_placeholder()

    def focus(self):
        self.entry.focus_set()

    def on_return(self, callback):
        self.entry.bind("<Return>", lambda _e: callback())


def make_table(parent, columns, height=10):
    """columns: list of (id, heading, width, anchor). Returns (container, treeview)."""
    box = tk.Frame(parent, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
    tree = ttk.Treeview(box, columns=[c[0] for c in columns], show="headings", height=height,
                        selectmode="browse")
    for cid, heading, width, anchor in columns:
        tree.heading(cid, text=heading, anchor=anchor)
        tree.column(cid, width=width, anchor=anchor, stretch=True, minwidth=60)
    scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    tree.tag_configure("odd", background="#fafbfd")
    tree.tag_configure("low", foreground=RED)
    tree.tag_configure("in", foreground=theme.GREEN)
    tree.tag_configure("out", foreground=RED)
    return box, tree


def fill_table(tree, rows, tags=None):
    """rows: list of value tuples; tags: optional parallel list of extra tag tuples."""
    tree.delete(*tree.get_children())
    for i, values in enumerate(rows):
        extra = tuple(tags[i]) if tags else ()
        tree.insert("", "end", values=values, tags=extra + (("odd",) if i % 2 else ()))


class ModalDialog(tk.Toplevel):
    """A centred, modal window. Subclasses build their UI inside ``self.body``."""

    def __init__(self, master, title, width, height):
        super().__init__(master.winfo_toplevel(), bg=WHITE)
        self.title(title)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.body = tk.Frame(self, bg=WHITE, padx=24, pady=20)
        self.body.pack(fill="both", expand=True)
        theme.center_window(self, width, height, master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

    def go_modal(self):
        self.wait_visibility()
        self.grab_set()
        self.focus_set()
        self.wait_window()
