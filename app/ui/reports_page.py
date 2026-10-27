import csv
import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog, messagebox

from ..errors import AppError
from ..services import ReportService
from .pages import BasePage
from .theme import MUTED, RED, TEXT, WHITE, font
from .widgets import PlaceholderEntry, fill_table, make_button, make_table


class ReportsPage(BasePage):
    title = "Inventory Report"

    def __init__(self, master, main):
        super().__init__(master, main)
        self.service = ReportService()
        self.rows = []
        self.range = ("", "")

        bar = tk.Frame(self.body, bg=WHITE)
        bar.pack(fill="x", pady=(0, 10))
        today = date.today()
        self.start = PlaceholderEntry(bar, "From (YYYY-MM-DD)", width=18)
        self.start.pack(side="left", fill="x", expand=True)
        self.end = PlaceholderEntry(bar, "To (YYYY-MM-DD)", width=18)
        self.end.pack(side="left", fill="x", expand=True, padx=10)
        self.start.set(today.replace(day=1).isoformat())
        self.end.set(today.isoformat())
        self.start.on_return(self.generate)
        self.end.on_return(self.generate)
        make_button(bar, "Generate", self.generate).pack(side="left")
        self.export_btn = make_button(bar, "Export CSV", self.export, kind="secondary")
        self.export_btn.pack(side="left", padx=(8, 0))

        presets = tk.Frame(self.body, bg=WHITE)
        presets.pack(fill="x", pady=(0, 10))
        tk.Label(presets, text="Quick range:", bg=WHITE, fg=MUTED, font=font(9)).pack(side="left")
        make_button(presets, "This month", self.this_month, kind="secondary", pady=5).pack(
            side="left", padx=(8, 0))
        make_button(presets, "Last 30 days", self.last_30_days, kind="secondary", pady=5).pack(
            side="left", padx=(8, 0))

        box, self.tree = make_table(self.body, [("product", "Product", 280, "w"), ("stock", "Total Stock", 120, "w"),
                                                ("received", "Total Received", 130, "w"),
                                                ("sold", "Total Sold", 120, "w")])
        box.pack(fill="both", expand=True)
        self.status = tk.Label(self.body, text="", bg=WHITE, fg=MUTED, font=font(9), justify="left")
        self.status.pack(anchor="w", pady=(6, 0))
        self.generate()

    def _set_range(self, start, end):
        self.start.set(start.isoformat())
        self.end.set(end.isoformat())
        self.generate()

    def this_month(self):
        today = date.today()
        self._set_range(today.replace(day=1), today)

    def last_30_days(self):
        today = date.today()
        self._set_range(today - timedelta(days=29), today)

    def generate(self):
        try:
            rows = self.service.inventory_report(self.start.get(), self.end.get())
        except AppError as exc:
            self.status.config(fg=RED, text=str(exc))
            return
        self.rows, self.range = rows, (self.start.get().strip(), self.end.get().strip())
        fill_table(self.tree, [(r["product_name"], r["total_stock"], r["total_received"], r["total_sold"])
                               for r in rows])
        if not rows:
            self.status.config(fg=MUTED, text="No products to report on yet.")
            return
        self.status.config(
            fg=TEXT,
            text=f"{len(rows)} product(s)  |  Stock on hand: {sum(r['total_stock'] for r in rows):,}  |  "
                 f"Received {self.range[0]} to {self.range[1]}: {sum(r['total_received'] for r in rows):,}  |  "
                 f"Sold: {sum(r['total_sold'] for r in rows):,}")

    def export(self):
        if not self.rows:
            messagebox.showinfo("Export", "Generate a report with at least one product first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save report", defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
            initialfile=f"inventory_report_{self.range[0]}_to_{self.range[1]}.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Product", "Total Stock", "Total Received", "Total Sold"])
                for r in self.rows:
                    writer.writerow([r["product_name"], r["total_stock"], r["total_received"], r["total_sold"]])
        except OSError as exc:
            messagebox.showerror("Export", f"Could not save the file:\n{exc}")
            return
        messagebox.showinfo("Export", "Report saved.")
