"""Colours, fonts and shared styling (matches the Inventoria system design)."""
import tkinter as tk
from tkinter import ttk

NAVY = "#13294b"
NAVY_HOVER = "#1d3a68"
BLUE = "#1f6feb"
BLUE_HOVER = "#1859c4"
BG = "#f1f3f6"
WHITE = "#ffffff"
TEXT = "#16213e"
MUTED = "#6b7a90"
BORDER = "#dce3ec"
RED = "#d92d20"
RED_HOVER = "#b42318"
GREEN = "#15803d"
ORANGE = "#f59e0b"
ROW_SELECT = "#e8f0fe"

CARD_COLORS = {            # (background, label colour, number colour)
    "blue":   ("#dbe8fd", "#1e3a8a", "#1e3a8a"),
    "green":  ("#dcfce7", "#166534", "#166534"),
    "orange": ("#ffedd5", "#9a3412", "#9a3412"),
    "purple": ("#ede9fe", "#5b21b6", "#5b21b6"),
}

FONT_FAMILY = "Segoe UI"


def font(size=10, weight="normal"):
    return (FONT_FAMILY, size, weight)


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=font(10), background=WHITE, foreground=TEXT)

    style.configure("Treeview", rowheight=34, background=WHITE, fieldbackground=WHITE,
                    foreground=TEXT, borderwidth=0, font=font(10))
    style.configure("Treeview.Heading", background=WHITE, foreground=MUTED, font=font(10, "bold"),
                    relief="flat", borderwidth=0, padding=(8, 8))
    style.map("Treeview", background=[("selected", ROW_SELECT)], foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", WHITE)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure("TCombobox", padding=6, fieldbackground=WHITE, background=WHITE,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, arrowcolor=MUTED)
    style.map("TCombobox", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)],
              darkcolor=[("focus", BLUE)], fieldbackground=[("readonly", WHITE)])
    style.configure("Vertical.TScrollbar", background=BORDER, troughcolor=WHITE, bordercolor=WHITE,
                    arrowcolor=MUTED, relief="flat")
    root.option_add("*TCombobox*Listbox.font", font(10))


def center_window(win, width, height, parent=None):
    win.update_idletasks()
    if parent is not None:
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    else:
        x = (win.winfo_screenwidth() - width) // 2
        y = (win.winfo_screenheight() - height) // 3
    win.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
