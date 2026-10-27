import tkinter as tk

from controllers import StockController
from core.formatting import product_label
from ui import theme
from ui.theme import Btn, ComboField, Field, Page


class StockPage(Page):
    title = "Stock Management"
    subtitle = ("Add Stock when items arrive; Remove Stock when items are sold or used. "
                "1) find the product  2) type the quantity  3) Submit. Every movement is recorded.")

    def build(self):
        self.ctrl = StockController()
        s = self.app.session
        self.modes = [(m, label) for m, label, perm in (("IN", "Add Stock", "stock.in"), ("OUT", "Remove Stock", "stock.out"))
                      if s.has_permission(perm)]
        wanted = getattr(self.app, "pending_mode", None)
        self.app.pending_mode = None
        self.mode = wanted if wanted in dict(self.modes) else self.modes[0][0]
        tabs = tk.Frame(self.body, bg="white")
        tabs.pack(fill="x", pady=(0, 14))
        self.tab_buttons = {}
        for i, (mode, label) in enumerate(self.modes):
            tabs.columnconfigure(i, weight=1, uniform="tabs")
            btn = Btn(tabs, label, lambda m=mode: self.set_mode(m))
            btn.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0), ipady=4)
            self.tab_buttons[mode] = btn
        form = tk.Frame(self.body, bg="white")
        form.pack(fill="x")
        self.search = Field(form, "Search product, specification or SKU")
        self.search.pack(fill="x", pady=(0, 10))
        self.search.entry.bind("<KeyRelease>", lambda e: self.load_products())
        self.product = ComboField(form, "Product", width=60)
        self.product.pack(fill="x")
        self.product.on_change(self.show_info)
        self.info = tk.Label(form, text="", bg="white", fg=theme.MUTED, anchor="w", font=theme.font(10))
        self.info.pack(fill="x", pady=(4, 10))
        self.qty = Field(form, "Quantity (number of listed selling units)")
        self.qty.pack(fill="x", pady=(0, 10))
        self.qty.entry.bind("<Return>", lambda e: self.submit())
        self.remarks = Field(form, "Remarks (optional)")
        self.remarks.pack(fill="x", pady=(0, 14))
        self.submit_btn = Btn(form, "Submit", self.submit)
        self.submit_btn.pack(fill="x", ipady=4)
        self.result = tk.Label(form, text="", bg="white", anchor="w", justify="left", wraplength=800,
                               font=theme.font(11, "bold"))
        self.result.pack(fill="x", pady=(14, 0))
        self.set_mode(self.mode)

    def set_mode(self, mode):
        self.mode = mode
        for m, btn in self.tab_buttons.items():
            btn.set_kind("primary" if m == mode else "secondary")
        self.submit_btn.config(text="Add to stock" if mode == "IN" else "Remove from stock")
        self.submit_btn.set_kind("primary" if mode == "IN" else "danger")
        self.result.config(text="")

    def refresh(self):
        self.load_products()

    def load_products(self, keep=None):
        keep = keep or self.product.value()
        self.items = {p["product_id"]: p for p in self.ctrl.search_products(self.search.get())}
        self.product.set_options([(f"{product_label(p['product_name'], p['specification'])}  "
                                   f"({p['sku']})  -  "
                                   f"{p['stock_quantity']} in stock", pid)
                                  for pid, p in self.items.items()])
        if not self.product.select_value(keep):
            self.product.select_first()
        self.show_info()

    def show_info(self):
        p = self.items.get(self.product.value())
        self.info.config(text=(f"Specification: {p['specification'] or 'Not entered'}   ·   "
                               f"Current stock: {p['stock_quantity']}   ·   "
                               f"Alert level: {p['low_stock_threshold']}")
                         if p else "No matching product.")

    def submit(self):
        pid = self.product.value()
        self.result.config(text="")
        res = self.ctrl.submit(pid, self.qty.get(), self.mode, self.remarks.get())
        verb = "Added" if res["mode"] == "IN" else "Removed"
        text = (f"✔ {verb} {res['qty']} × {product_label(res['name'], res['specification'])}.  "
                f"Stock: {res['old']} → {res['new']}.")
        color = theme.GREEN
        if res["low"]:
            text += "\n⚠ This product is now at or below its low-stock alert level."
            color = theme.ORANGE
        self.result.config(text=text, fg=color)
        self.qty.clear()
        self.remarks.clear()
        self.load_products(keep=pid)
        self.qty.focus()
