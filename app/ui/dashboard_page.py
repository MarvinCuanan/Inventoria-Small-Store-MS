import tkinter as tk

from ..errors import AppError
from ..services import InventoryService
from ..session import Session
from .pages import BasePage
from .theme import CARD_COLORS, MUTED, RED, TEXT, WHITE, font
from .stock_page import StockPage
from .widgets import fill_table, make_button, make_table
from tkinter import messagebox


class DashboardPage(BasePage):
    title = "Dashboard"

    def __init__(self, master, main):
        super().__init__(master, main)
        make_button(self.header_right, "Refresh", lambda: self.main.navigate("Dashboard", DashboardPage),
                    kind="secondary").pack(side="right")
        try:
            data = InventoryService().dashboard()
        except AppError as exc:
            messagebox.showerror("Dashboard", str(exc))
            return

        grid = tk.Frame(self.body, bg=WHITE)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1, uniform="cards")
        cards = [("Total Products", f"{data['total_products']:,}", "blue"),
                 ("Total Stock", f"{data['total_stock']:,}", "green"),
                 ("Low Stock", f"{data['low_stock']:,}", "orange"),
                 ("Today's Transactions", f"{data['today_transactions']:,}", "purple")]
        for i, (label, value, color) in enumerate(cards):
            bg, label_fg, number_fg = CARD_COLORS[color]
            card = tk.Frame(grid, bg=bg, padx=16, pady=10)
            card.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 10) if i % 2 == 0 else 0,
                      pady=(0, 10))
            tk.Label(card, text=label, bg=bg, fg=label_fg, font=font(9)).pack(anchor="w")
            tk.Label(card, text=value, bg=bg, fg=number_fg, font=font(22, "bold")).pack(anchor="w")

        heading = "Low Stock Alert"
        if Session.can("stock.add") or Session.can("stock.remove"):
            heading += "  ·  Double-click an item to adjust its stock"
        tk.Label(self.body, text=heading, bg=WHITE, fg=TEXT, font=font(13, "bold")).pack(
            anchor="w", pady=(10, 6))
        items = data["low_stock_items"]
        if not items:
            tk.Label(self.body, text="All products are well stocked.", bg=WHITE, fg=MUTED,
                     font=font(10)).pack(anchor="w", pady=8)
            return
        box, tree = make_table(self.body, [("product", "Product", 320, "w"),
                                           ("stock", "Current Stock", 140, "w"),
                                           ("limit", "Alert Level", 140, "w"),
                                           ("status", "Status", 120, "w")])
        box.pack(fill="both", expand=True)
        if Session.can("stock.add") or Session.can("stock.remove"):
            def open_stock(event):
                iid = tree.identify_row(event.y)
                if iid:
                    product_name = tree.item(iid, "values")[0]
                    self.main.navigate("Stock", StockPage, product_name)

            tree.bind("<Double-1>", open_stock)
        rows, tags = [], []
        for p in items:
            out = p["stock_quantity"] == 0
            rows.append((p["product_name"], p["stock_quantity"], f"\u2264 {p['low_stock_threshold']}",
                         "Out of stock" if out else "Low"))
            tags.append(("low",))
        fill_table(tree, rows, tags)
