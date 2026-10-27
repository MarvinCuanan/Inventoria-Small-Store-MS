import tkinter as tk

import config
from controllers import DashboardController
from core.errors import AppError
from core.formatting import product_label, stock_status
from ui import theme
from ui.theme import Btn, DataTable, Page


class DashboardPage(Page):
    title = "Dashboard"
    subtitle = "Today's overview. Items in the red list need restocking - use Add Stock when they arrive."

    def build(self):
        self.ctrl = DashboardController()
        s = self.app.session
        me = s.current_user
        quick = tk.Frame(self.body, bg="white")
        quick.pack(fill="x", pady=(0, 6))
        tk.Label(quick, text=f"Welcome, {me['full_name']}!  Quick actions:", bg="white", fg=theme.TEXT,
                 font=theme.font(11, "bold")).pack(side="left", padx=(6, 12))
        for label, perm, action, kind in (("Add Stock", "stock.in", lambda: self.open_stock("IN"), "primary"),
                                          ("Remove Stock", "stock.out", lambda: self.open_stock("OUT"), "secondary"),
                                          ("Find a Product", "product.view", lambda: self.go("products"), "secondary")):
            if s.has_permission(perm):
                Btn(quick, label, action, kind).pack(side="left", padx=(0, 8))
        grid = tk.Frame(self.body, bg="white")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1, uniform="cards")
        self.values = {}
        cards = [("total_products", "Total Products", "#dbeafe", "#1e3a8a"),
                 ("total_stock", "Total Stock", "#dcfce7", "#166534"),
                 ("low_stock", "Low Stock", "#ffedd5", "#9a3412"),
                 ("today_transactions", "Today's Transactions", "#ede9fe", "#5b21b6")]
        for i, (key, label, bg, fg) in enumerate(cards):
            card = tk.Frame(grid, bg=bg, padx=18, pady=12)
            card.grid(row=i // 2, column=i % 2, sticky="ew", padx=6, pady=6)
            tk.Label(card, text=label, bg=bg, fg=fg, font=theme.font(11)).pack(anchor="w")
            self.values[key] = tk.Label(card, text="0", bg=bg, fg=fg, font=theme.font(26, "bold"))
            self.values[key].pack(anchor="w")
        tk.Label(self.body, text="Low Stock Alert", bg="white", fg=theme.TEXT,
                 font=theme.font(14, "bold")).pack(anchor="w", pady=(14, 6))
        self.table = DataTable(self.body, [("p", "Product", 320, "w"), ("s", "Current Stock", 120, "center"),
                                           ("t", "Alert Level", 120, "center"), ("st", "Status", 120, "center")], height=8)
        self.table.pack(fill="both", expand=True)
        Btn(self.actions, "Refresh", self.refresh, "secondary").pack()
        self._job = self.after(config.DASHBOARD_REFRESH_MS, self._auto)

    def open_stock(self, mode):
        self.app.pending_mode = mode
        self.go("stock")

    def refresh(self):
        data = self.ctrl.get_summary()
        for key, label in self.values.items():
            label.config(text=f"{data[key]:,}")
        self.table.load([(r["product_id"],
                          (product_label(r["product_name"], r["specification"]), r["stock_quantity"],
                           r["low_stock_threshold"],
                           stock_status(r["stock_quantity"], r["low_stock_threshold"])), "low")
                         for r in data["low_items"]])

    def _auto(self):
        try:
            self.refresh()
        except (AppError, tk.TclError):
            pass
        self._job = self.after(config.DASHBOARD_REFRESH_MS, self._auto)

    def destroy(self):
        try:
            self.after_cancel(self._job)
        except (AttributeError, tk.TclError, ValueError):
            pass
        super().destroy()
