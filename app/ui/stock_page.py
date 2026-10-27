import tkinter as tk
from tkinter import messagebox, ttk

from ..errors import AppError
from ..services import STOCK_IN, STOCK_OUT, InventoryService
from ..session import Session
from .pages import BasePage
from .theme import BLUE, BLUE_HOVER, BORDER, GREEN, MUTED, RED, TEXT, WHITE, font
from .widgets import PlaceholderEntry, make_button

_NAV_KEYS = {"Up", "Down", "Left", "Right", "Return", "Tab", "Escape", "Shift_L", "Shift_R",
             "Control_L", "Control_R", "Home", "End", "Prior", "Next"}


class StockPage(BasePage):
    title = "Stock Management"

    def __init__(self, master, main, initial_product=None):
        super().__init__(master, main)
        self.service = InventoryService()
        self.kind = STOCK_IN if Session.can("stock.add") else STOCK_OUT
        self.products = {}
        try:
            self._load_products()
        except AppError as exc:
            messagebox.showerror("Stock", str(exc))

        modes = tk.Frame(self.body, bg=WHITE)
        modes.pack(fill="x")
        modes.columnconfigure((0, 1), weight=1, uniform="m")
        self.btn_in = self.btn_out = None
        if Session.can("stock.add"):
            self.btn_in = tk.Button(modes, text="Add Stock", relief="flat", bd=0, cursor="hand2", pady=8,
                                    font=font(10, "bold"), command=lambda: self.set_kind(STOCK_IN),
                                    highlightthickness=1, highlightbackground=BORDER)
            self.btn_in.grid(row=0, column=0, sticky="ew",
                             padx=(0, 6) if Session.can("stock.remove") else 0, columnspan=1 if Session.can("stock.remove") else 2)
        if Session.can("stock.remove"):
            self.btn_out = tk.Button(modes, text="Remove Stock", relief="flat", bd=0, cursor="hand2", pady=8,
                                     font=font(10, "bold"), command=lambda: self.set_kind(STOCK_OUT),
                                     highlightthickness=1, highlightbackground=BORDER)
            self.btn_out.grid(row=0, column=1 if Session.can("stock.add") else 0, sticky="ew",
                              padx=(6, 0) if Session.can("stock.add") else 0,
                              columnspan=1 if Session.can("stock.add") else 2)

        form = tk.Frame(self.body, bg=WHITE)
        form.pack(fill="x", pady=(16, 0))
        tk.Label(form, text="Product", bg=WHITE, fg=TEXT, font=font(11)).pack(anchor="w", pady=(0, 4))
        product_row = tk.Frame(form, bg=WHITE)
        product_row.pack(fill="x")
        make_button(product_row, "Refresh", self.refresh_products, kind="secondary").pack(side="right")
        self.product_box = ttk.Combobox(product_row, values=sorted(self.products), font=font(10))
        self.product_box.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        self.product_box.bind("<<ComboboxSelected>>", self._show_info)
        self.product_box.bind("<KeyRelease>", self._filter)
        self.product_box.bind("<FocusOut>", self._show_info)
        if initial_product in self.products:
            self.product_box.set(initial_product)
        self.info = tk.Label(form, text="Start typing to search, or pick a product from the list.",
                             bg=WHITE, fg=MUTED, font=font(9))
        self.info.pack(anchor="w", pady=(4, 10))

        tk.Label(form, text="Quantity", bg=WHITE, fg=TEXT, font=font(11)).pack(anchor="w", pady=(0, 4))
        self.quantity = PlaceholderEntry(form, "e.g. 10")
        self.quantity.pack(fill="x")
        tk.Label(form, text="Remarks (optional)", bg=WHITE, fg=TEXT, font=font(11)).pack(anchor="w", pady=(12, 4))
        self.remarks = PlaceholderEntry(form, "e.g. Delivery from supplier")
        self.remarks.pack(fill="x")
        self.quantity.on_return(self.submit)
        self.remarks.on_return(self.submit)

        make_button(form, "Submit", self.submit, pady=10).pack(fill="x", pady=(16, 0))
        self.result = tk.Label(form, text="", bg=WHITE, font=font(10), wraplength=700, justify="left")
        self.result.pack(anchor="w", pady=(12, 0))
        self.set_kind(self.kind)
        if initial_product in self.products:
            self._show_info()

    # ---- helpers ----
    def _load_products(self):
        self.products = {p["product_name"]: p for p in self.service.product_names()}

    def refresh_products(self):
        try:
            selected = self.product_box.get().strip()
            self._load_products()
            self.product_box["values"] = sorted(self.products)
            if selected in self.products:
                self.product_box.set(selected)
            self._show_info()
            self.result.config(fg=GREEN, text="Product list refreshed.")
        except AppError as exc:
            self.result.config(fg=RED, text=f"Could not refresh products: {exc}")

    def set_kind(self, kind):
        button = self.btn_in if kind == STOCK_IN else self.btn_out
        if button is None:
            return
        self.kind = kind
        for btn, active in ((self.btn_in, kind == STOCK_IN), (self.btn_out, kind == STOCK_OUT)):
            if btn is not None:
                btn.config(bg=BLUE if active else WHITE, fg=WHITE if active else TEXT,
                           activebackground=BLUE_HOVER if active else "#eef2f7",
                           activeforeground=WHITE if active else TEXT)
        self.result.config(text="")

    def _filter(self, event):
        if event.keysym in _NAV_KEYS:
            return
        typed = self.product_box.get().strip().lower()
        names = sorted(self.products)
        self.product_box["values"] = [n for n in names if typed in n.lower()] if typed else names

    def _selected(self):
        typed = self.product_box.get().strip().lower()
        for name, product in self.products.items():
            if name.lower() == typed:
                return product
        return None

    def _show_info(self, _e=None):
        p = self._selected()
        if p:
            self.info.config(fg=MUTED, text=f"Current stock: {p['stock_quantity']}   |   "
                                            f"Alert level: {p['low_stock_threshold']}   |   "
                                            f"Price: \u20b1{p['price']:,.2f}")
        elif self.product_box.get().strip():
            self.info.config(fg=RED, text="No product with that name. Pick one from the list.")
        else:
            self.info.config(fg=MUTED, text="Start typing to search, or pick a product from the list.")

    # ---- submit ----
    def submit(self):
        self.result.config(text="")
        product = self._selected()
        if product is None:
            self.result.config(fg=RED, text="Please choose a product from the list.")
            return
        try:
            res = self.service.adjust_stock(product["product_id"], self.quantity.get(), self.kind,
                                            self.remarks.get())
        except AppError as exc:
            self.result.config(fg=RED, text=str(exc))
            return
        verb = "added to" if self.kind == STOCK_IN else "removed from"
        text = f"Done. Stock {verb} {res['name']}. New stock: {res['stock']}."
        if res["low"]:
            text += f"\nWarning: {res['name']} is low on stock (alert level {res['threshold']}). Time to restock."
        self.result.config(fg=GREEN if not res["low"] else "#b45309", text=text)
        self.quantity.clear()
        self.remarks.clear()
        try:
            self._load_products()
            self.product_box["values"] = sorted(self.products)
        except AppError as exc:
            text += f"\nWarning: the stock change was saved, but products could not be refreshed: {exc}"
            self.result.config(fg="#b45309", text=text)
            self.quantity.clear()
            self.remarks.clear()
            return
        self.product_box.set(res["name"])
        self._show_info()
