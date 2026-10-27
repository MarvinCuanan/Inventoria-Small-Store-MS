import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

from controllers import ReportController
from core.formatting import money
from ui import theme
from ui.theme import Btn, DataTable, Field, Page


class ReportsPage(Page):
    title = "Inventory Report"
    subtitle = "Pick a date range and press Generate. Stock In / Total Sold count only movements inside that range."

    def build(self):
        self.ctrl = ReportController()
        self.report = None
        Btn(self.actions, "Export CSV", self.export, "secondary").pack()
        bar = tk.Frame(self.body, bg="white")
        bar.pack(fill="x")
        today = date.today()
        self.d_from = Field(bar, "From (YYYY-MM-DD)", width=16)
        self.d_from.pack(side="left", padx=(0, 8))
        self.d_from.set(today.replace(day=1).isoformat())
        self.d_to = Field(bar, "To (YYYY-MM-DD)", width=16)
        self.d_to.pack(side="left", padx=(0, 8))
        self.d_to.set(today.isoformat())
        Btn(bar, "Generate", self.refresh).pack(side="left", anchor="s")
        self.summary = tk.Label(self.body, text="", bg="#f1f5f9", fg=theme.TEXT, anchor="w", justify="left",
                                padx=12, pady=8, font=theme.font(11))
        self.summary.pack(fill="x", pady=(12, 10))
        self.table = DataTable(self.body, [("p", "Product", 150, "w"), ("sp", "Specification / unit", 180, "w"),
                                           ("c", "Category", 110, "w"), ("pr", "Price", 80, "e"),
                                           ("s", "Total Stock", 90, "center"),
                                           ("i", "Stock In", 80, "center"), ("o", "Total Sold", 90, "center"),
                                           ("st", "Status", 90, "center")], height=14)
        self.table.pack(fill="both", expand=True)
        for f in (self.d_from, self.d_to):
            f.entry.bind("<Return>", lambda e: self.refresh())

    def refresh(self):
        rep = self.report = self.ctrl.generate(self.d_from.get(), self.d_to.get())
        self.table.load([(r["product_id"], (r["product_name"],
                                            r["specification"] or "Not specified",
                                            r["category_name"], money(r["price"]),
                                            r["stock_quantity"], r["total_in"], r["total_out"], r["status"]),
                          None if r["status"] == "OK" else "low") for r in rep["rows"]])
        self.summary.config(text=(
            f"Period {rep['from']} to {rep['to']}     Products: {rep['products']}     "
            f"Units in stock: {rep['units_in_stock']:,}     Stock value: {money(rep['stock_value'])}\n"
            f"Units received: {rep['units_in']:,}     Units sold: {rep['units_sold']:,}     "
            f"Need restocking: {rep['low_items']}"))

    def export(self):
        if not self.report or not self.report["rows"]:
            messagebox.showinfo("Export", "Generate a report with at least one product first.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
                                            initialfile=f"inventory_report_{self.report['from']}_to_{self.report['to']}.csv")
        if path:
            self.ctrl.export_csv(path, self.report)
            messagebox.showinfo("Export", "Saved. You can open it in Excel.", parent=self)
