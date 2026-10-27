"""Base class shared by all pages inside the main window."""
import tkinter as tk

from .theme import TEXT, WHITE, font


class BasePage(tk.Frame):
    title = ""

    def __init__(self, master, main):
        super().__init__(master, bg=WHITE)
        self.main = main
        header = tk.Frame(self, bg=WHITE)
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(header, text=self.title, bg=WHITE, fg=TEXT, font=font(17, "bold")).pack(side="left")
        self.header_right = tk.Frame(header, bg=WHITE)
        self.header_right.pack(side="right")
        self.body = tk.Frame(self, bg=WHITE)
        self.body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
