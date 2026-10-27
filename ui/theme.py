"""Look-and-feel shared by every screen: colours, fonts, buttons, form fields, tables, dialogs."""
import tkinter as tk
from tkinter import ttk, font as tkfont

NAVY, NAVY_HOVER = "#132a4f", "#1d3a6b"
BLUE, BLUE_HOVER = "#2070ea", "#1a5fd0"
TEXT, MUTED, BORDER, SOFT = "#12213f", "#64748b", "#e2e8f0", "#f8fafc"
GREEN, RED, ORANGE = "#16a34a", "#dc2626", "#d97706"
FONT_FAMILY = "Arial"


def font(size=11, weight="normal"):
    return (FONT_FAMILY, size, weight)


def init_theme(root):
    global FONT_FAMILY
    available = set(tkfont.families(root))
    FONT_FAMILY = next((f for f in ("Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial") if f in available), "Arial")
    root.option_add("*Font", (FONT_FAMILY, 11))
    style = ttk.Style(root)
    style.theme_use("clam")
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background="white", fieldbackground="white", foreground=TEXT,
                    rowheight=32, borderwidth=0, font=(FONT_FAMILY, 11))
    style.configure("Treeview.Heading", background="white", foreground=MUTED, relief="flat",
                    borderwidth=0, padding=(8, 8), font=(FONT_FAMILY, 11, "bold"))
    style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", "#f1f5f9")])
    style.configure("TCombobox", padding=6)


def center_window(win, width, height, parent=None):
    win.update_idletasks()
    if parent is not None and parent.winfo_viewable():
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    else:
        x = (win.winfo_screenwidth() - width) // 2
        y = (win.winfo_screenheight() - height) // 2
    win.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")


class Btn(tk.Button):
    KINDS = {"primary": (BLUE, "white", BLUE_HOVER), "secondary": ("white", TEXT, "#eef2f7"),
             "danger": (RED, "white", "#b91c1c"), "success": (GREEN, "white", "#15803d")}

    def __init__(self, parent, text, command=None, kind="primary", **kw):
        super().__init__(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2",
                         font=font(11, "bold"), padx=16, pady=8, highlightthickness=1, **kw)
        self.set_kind(kind)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

    def set_kind(self, kind):
        self._bg, fg, self._hover = self.KINDS[kind]
        self.config(bg=self._bg, fg=fg, activebackground=self._hover, activeforeground=fg,
                    highlightbackground=BORDER if kind == "secondary" else self._bg)


class Field(tk.Frame):
    """A label above a text box. secret=True adds a Show/Hide toggle for passwords."""

    def __init__(self, parent, label, secret=False, bg="white", width=None):
        super().__init__(parent, bg=bg)
        self.secret = secret
        tk.Label(self, text=label, bg=bg, fg=MUTED, font=font(10, "bold"), anchor="w").pack(fill="x")
        self.box = tk.Frame(self, bg="white", highlightthickness=1, highlightbackground=BORDER, highlightcolor=BLUE)
        self.box.pack(fill="x", pady=(3, 0))
        self.var = tk.StringVar()
        opts = {"width": width} if width else {}
        self.entry = tk.Entry(self.box, textvariable=self.var, relief="flat", bd=0, font=font(12), bg="white",
                              fg=TEXT, insertbackground=TEXT, show="•" if secret else "", **opts)
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=8)
        if secret:
            eye = tk.Label(self.box, text="Show", bg="white", fg=BLUE, cursor="hand2", font=font(10, "bold"))
            eye.pack(side="right", padx=8)
            eye.bind("<Button-1>", lambda e: self._toggle(eye))
        self.entry.bind("<FocusIn>", lambda e: self.box.config(highlightbackground=BLUE))
        self.entry.bind("<FocusOut>", lambda e: self.box.config(highlightbackground=BORDER))

    def _toggle(self, eye):
        hidden = bool(self.entry.cget("show"))
        self.entry.config(show="" if hidden else "•")
        eye.config(text="Hide" if hidden else "Show")

    def get(self):
        value = self.var.get()
        return value if self.secret else value.strip()

    def set(self, value):
        self.var.set("" if value is None else str(value))

    def clear(self):
        self.var.set("")

    def focus(self):
        self.entry.focus_set()


class ComboField(tk.Frame):
    """A label above a read-only dropdown whose items are (text, value) pairs."""

    def __init__(self, parent, label, options=None, bg="white", width=24):
        super().__init__(parent, bg=bg)
        tk.Label(self, text=label, bg=bg, fg=MUTED, font=font(10, "bold"), anchor="w").pack(fill="x")
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.var, state="readonly", font=font(12), width=width)
        self.combo.pack(fill="x", pady=(3, 0))
        self._map = {}
        self.set_options(options or [])

    def set_options(self, options):
        self._map = {text: value for text, value in options}
        self.combo["values"] = [text for text, _ in options]

    def value(self):
        return self._map.get(self.var.get())

    def text(self):
        return self.var.get()

    def select_value(self, value):
        for text, val in self._map.items():
            if val == value:
                self.var.set(text)
                return True
        return False

    def select_first(self):
        values = self.combo["values"]
        self.var.set(values[0] if values else "")

    def on_change(self, callback):
        self.combo.bind("<<ComboboxSelected>>", lambda e: callback())


class DataTable(tk.Frame):
    """Scrollable table. columns = [(key, title, width, anchor)]; load([(iid, values, tag), ...])."""

    def __init__(self, parent, columns, height=12):
        super().__init__(parent, bg="white", highlightthickness=1, highlightbackground=BORDER)
        self._keys = [c[0] for c in columns]
        self._descending = {}
        self.tree = ttk.Treeview(self, columns=self._keys, show="headings", height=height, selectmode="browse")
        for key, title, width, anchor in columns:
            self.tree.heading(key, text=title, anchor=anchor if anchor != "e" else "e",
                              command=lambda k=key: self._sort(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=True)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for tag, color in (("low", RED), ("in", GREEN), ("out", RED), ("muted", "#94a3b8"), ("warn", ORANGE)):
            self.tree.tag_configure(tag, foreground=color)
        self.empty = tk.Label(self, text="No records found.", bg="white", fg=MUTED, font=font(11))

    def load(self, items):
        self.tree.delete(*self.tree.get_children())
        for iid, values, tag in items:
            self.tree.insert("", "end", iid=str(iid), values=values, tags=(tag,) if tag else ())
        if items:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.4, anchor="center")

    def selected(self):
        chosen = self.tree.selection()
        return chosen[0] if chosen else None

    def on_double_click(self, callback):
        self.tree.bind("<Double-1>", lambda e: callback() if self.selected() else None)

    def _sort(self, key):
        idx = self._keys.index(key)
        reverse = self._descending.get(key, False)

        def sort_key(iid):
            raw = str(self.tree.item(iid, "values")[idx]).replace("₱", "").replace(",", "").replace("+", "")
            try:
                return (0, float(raw), "")
            except ValueError:
                return (1, 0.0, raw.lower())

        for pos, iid in enumerate(sorted(self.tree.get_children(""), key=sort_key, reverse=reverse)):
            self.tree.move(iid, "", pos)
        self._descending[key] = not reverse


class Page(tk.Frame):
    """Base for every screen in the main window: title row, action area, body."""
    title = ""
    subtitle = ""

    def get_subtitle(self):
        return self.subtitle

    def go(self, key):
        """Jump to another screen of the main window."""
        self.app.frame.show_page(key)

    def __init__(self, parent, app):
        super().__init__(parent, bg="white")
        self.app = app
        head = tk.Frame(self, bg="white")
        head.pack(fill="x", padx=28, pady=(22, 10))
        left = tk.Frame(head, bg="white")
        left.pack(side="left")
        tk.Label(left, text=self.title, font=font(20, "bold"), fg=TEXT, bg="white").pack(anchor="w")
        hint = self.get_subtitle()
        if hint:
            tk.Label(left, text=hint, font=font(10), fg=MUTED, bg="white", justify="left",
                     wraplength=720).pack(anchor="w", pady=(2, 0))
        self.actions = tk.Frame(head, bg="white")
        self.actions.pack(side="right")
        self.body = tk.Frame(self, bg="white")
        self.body.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        self.build()
        self.refresh()

    def build(self):
        pass

    def refresh(self):
        pass


class Dialog(tk.Toplevel):
    """Modal pop-up with Save / Cancel. Subclasses implement build(body) and on_save()."""

    def __init__(self, parent, title, width=440, save_text="Save"):
        top = parent.winfo_toplevel()
        super().__init__(top, bg="white")
        self.title(title)
        self.transient(top)
        self.resizable(False, False)
        self.body = tk.Frame(self, bg="white", padx=24, pady=20)
        self.body.pack(fill="both", expand=True)
        self.build(self.body)
        bar = tk.Frame(self, bg=SOFT, padx=24, pady=12)
        bar.pack(fill="x")
        Btn(bar, "Cancel" if save_text else "Close", self.destroy, "secondary").pack(side="right", padx=(8, 0))
        if save_text:
            Btn(bar, save_text, self.on_save).pack(side="right")
            self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        center_window(self, width, self.winfo_reqheight(), top)
        self.wait_visibility()
        self.grab_set()

    def build(self, body):
        pass

    def on_save(self):
        pass
