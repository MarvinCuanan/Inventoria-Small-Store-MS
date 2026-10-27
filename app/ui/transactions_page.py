import tkinter as tk
from tkinter import messagebox, ttk

from ..errors import AppError
from ..services import InventoryService
from .pages import BasePage
from .theme import MUTED, RED, WHITE, font
from .widgets import PlaceholderEntry, fill_table, make_button, make_table


class TransactionsPage(BasePage):
    title = "Transaction Records"

    def __init__(self, master, main):
        super().__init__(master, main)
        self.service = InventoryService()

        bar = tk.Frame(self.body, bg=WHITE)
        bar.pack(fill="x", pady=(0, 10))
        self.kind = ttk.Combobox(bar, values=["All", "Stock In", "Stock Out"], state="readonly",
                                 width=14, font=font(10))
        self.kind.set("All")
        self.kind.pack(side="left", ipady=4)
        self.day = PlaceholderEntry(bar, "Date (YYYY-MM-DD), optional", width=28)
        self.day.pack(side="left", fill="x", expand=True, padx=10)
        self.day.on_return(self.search)
        make_button(bar, "Search", self.search).pack(side="left")
        make_button(bar, "Clear", self.clear, kind="secondary").pack(side="left", padx=(8, 0))
        self.kind.bind("<<ComboboxSelected>>", lambda _e: self.search())

        box, self.tree = make_table(self.body, [("date", "Date", 150, "w"), ("product", "Product", 240, "w"),
                                                ("type", "Type", 110, "w"), ("qty", "Quantity", 90, "w"),
                                                ("user", "User", 120, "w"), ("remarks", "Remarks", 220, "w")])
        box.pack(fill="both", expand=True)
        self.status = tk.Label(self.body, text="", bg=WHITE, fg=MUTED, font=font(9))
        self.status.pack(anchor="w", pady=(6, 0))
        self.search()

    def clear(self):
        self.kind.set("All")
        self.day.clear()
        self.search()

    def search(self):
        try:
            rows = self.service.search_transactions(self.kind.get(), self.day.get())
        except AppError as exc:
            self.status.config(fg=RED, text=str(exc))
            return
        values, tags = [], []
        for r in rows:
            incoming = r["transaction_type"] == "Stock In"
            values.append((r["transaction_date"].strftime("%Y-%m-%d %H:%M"), r["product_name"],
                           r["transaction_type"], f"+{r['quantity']}" if incoming else f"-{r['quantity']}",
                           r["username"], r["remarks"] or ""))
            tags.append(("in",) if incoming else ("out",))
        fill_table(self.tree, values, tags)
        if rows:
            self.status.config(fg=MUTED, text=f"{len(rows)} record(s) shown (newest first, up to 500).")
        else:
            self.status.config(fg=MUTED, text="No transactions match your search.")
