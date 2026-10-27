import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

from controllers import TransactionController
from core.formatting import money, product_label, short_dt
from ui import theme
from ui.theme import Btn, ComboField, DataTable, Field, Page


class TransactionsPage(Page):
    title = "Transaction Records"

    def get_subtitle(self):
        if self.app.session.has_permission("transaction.view_all"):
            return "Every stock-in (green) and stock-out (red). Fill in any filters, then press Search."
        return "Your own stock-in (green) and stock-out (red) records. Fill in any filters, then press Search."

    def build(self):
        self.ctrl = TransactionController()
        self.is_all = self.app.session.has_permission("transaction.view_all")
        Btn(self.actions, "Export CSV", self.export, "secondary").pack()
        bar = tk.Frame(self.body, bg="white")
        bar.pack(fill="x")
        self.type = ComboField(bar, "Type", [("All", None), ("Stock In", "IN"), ("Stock Out", "OUT")], width=12)
        self.type.pack(side="left", padx=(0, 8))
        self.type.select_first()
        self.product = Field(bar, "Product (name / specification / SKU)", width=24)
        self.product.pack(side="left", padx=(0, 8))
        self.d_from = Field(bar, "From (YYYY-MM-DD)", width=13)
        self.d_from.pack(side="left", padx=(0, 8))
        self.d_to = Field(bar, "To (YYYY-MM-DD)", width=13)
        self.d_to.pack(side="left", padx=(0, 8))
        if self.is_all:
            users = [("All users", None)] + [(u["username"], u["user_id"]) for u in self.ctrl.list_users()]
            self.user = ComboField(bar, "User", users, width=14)
            self.user.pack(side="left", padx=(0, 8))
            self.user.select_first()
        btns = tk.Frame(bar, bg="white")
        btns.pack(side="left", anchor="s")
        Btn(btns, "Search", self.refresh).pack(side="left")
        Btn(btns, "Clear", self.clear, "secondary").pack(side="left", padx=(6, 0))
        self.note = tk.Label(self.body, text="" if self.is_all else "You can see your own transactions only.",
                             bg="white", fg=theme.MUTED, anchor="w")
        self.note.pack(fill="x", pady=(8, 4))
        self.table = DataTable(self.body, [("d", "Date", 130, "w"), ("p", "Product", 200, "w"), ("t", "Type", 90, "center"),
                                           ("q", "Quantity", 80, "e"), ("u", "Unit Price", 90, "e"),
                                           ("by", "User", 100, "w"), ("r", "Remarks", 180, "w")], height=14)
        self.table.pack(fill="both", expand=True)
        for f in (self.product, self.d_from, self.d_to):
            f.entry.bind("<Return>", lambda e: self.refresh())

    def refresh(self):
        self.rows = self.ctrl.list_transactions(self.type.value(), self.d_from.get(), self.d_to.get(),
                                                self.product.get(), self.user.value() if self.is_all else None)
        items = []
        for r in self.rows:
            is_in = r["transaction_type"] == "IN"
            sign = "+" if is_in else "-"
            label = product_label(r["product_name"], r["specification"])
            items.append((r["transaction_id"], (short_dt(r["transaction_date"]), label,
                                                "Stock In" if is_in else "Stock Out", f"{sign}{r['quantity']}",
                                                money(r["unit_price"]), r["username"], r["remarks"] or ""),
                          "in" if is_in else "out"))
        self.table.load(items)

    def clear(self):
        for f in (self.product, self.d_from, self.d_to):
            f.clear()
        self.type.select_first()
        if self.is_all:
            self.user.select_first()
        self.refresh()

    def export(self):
        if not self.rows:
            messagebox.showinfo("Export", "There is nothing to export for the current filters.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
                                            initialfile=f"transactions_{date.today().isoformat()}.csv")
        if path:
            self.ctrl.export_csv(path, self.rows)
            messagebox.showinfo("Export", "Saved. You can open it in Excel.", parent=self)
