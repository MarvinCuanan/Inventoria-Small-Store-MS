import tkinter as tk
from tkinter import messagebox

from controllers import ProductController
from core.formatting import money, stock_status
from ui import theme
from ui.theme import Btn, ComboField, DataTable, Dialog, Field, Page


class ProductDialog(Dialog):
    """Add (product=None) or edit a product."""

    def __init__(self, parent, ctrl, categories, on_done, product=None):
        self.ctrl, self.categories, self.on_done, self.product = ctrl, categories, on_done, product
        super().__init__(parent, "Edit product" if product else "Add product", 500)

    def build(self, body):
        p = self.product
        self.name = Field(body, "Product name")
        self.name.pack(fill="x", pady=(0, 10))
        self.specification = Field(body, "Specification / selling unit")
        self.specification.pack(fill="x", pady=(0, 4))
        tk.Label(body, text="Be precise, e.g. “1 sack (50 kg)”, “1 bag (5 kg)” or “1 bottle (500 ml)”. "
                           "Stock quantities are counted in this unit.",
                 bg="white", fg=theme.MUTED, font=theme.font(9), wraplength=390,
                 justify="left").pack(anchor="w", pady=(0, 10))
        self.sku = Field(body, "SKU / code (leave blank to auto-generate)")
        self.sku.pack(fill="x", pady=(0, 10))
        self.category = ComboField(body, "Category", [(c["category_name"], c["category_id"]) for c in self.categories])
        self.category.pack(fill="x", pady=(0, 10))
        row = tk.Frame(body, bg="white")
        row.pack(fill="x", pady=(0, 10))
        row.columnconfigure((0, 1), weight=1, uniform="r")
        self.price = Field(row, "Price (₱)")
        self.price.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.threshold = Field(row, "Low-stock alert level")
        self.threshold.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.threshold.set("10")
        self.active = tk.BooleanVar(value=True)
        if p is None:
            self.stock = Field(body, "Opening stock (number of listed selling units)")
            self.stock.pack(fill="x")
            self.stock.set("0")
            self.category.select_first()
        else:
            self.name.set(p["product_name"])
            self.specification.set(p["specification"])
            self.sku.set(p["sku"])
            self.category.select_value(p["category_id"])
            self.price.set(p["price"])
            self.threshold.set(p["low_stock_threshold"])
            self.active.set(bool(p["is_active"]))
            tk.Label(body, text=f"Current stock: {p['stock_quantity']}  (change it from the Stock page so "
                                "every movement is recorded)", bg="white", fg=theme.MUTED,
                     font=theme.font(10), wraplength=400, justify="left").pack(anchor="w")
            tk.Checkbutton(body, text="Product is active", variable=self.active, bg="white",
                           font=theme.font(11)).pack(anchor="w", pady=(8, 0))
        self.after(100, self.name.focus)

    def on_save(self):
        data = {"name": self.name.get(), "specification": self.specification.get(),
                "sku": self.sku.get(), "category_id": self.category.value(),
                "price": self.price.get(), "threshold": self.threshold.get(), "is_active": self.active.get()}
        if self.product is None:
            data["stock"] = self.stock.get()
            self.ctrl.add_product(data)
        else:
            self.ctrl.edit_product(self.product["product_id"], data)
        self.destroy()
        self.on_done()


class CategoryDialog(Dialog):
    def __init__(self, parent, ctrl, on_done):
        self.ctrl, self.on_done = ctrl, on_done
        super().__init__(parent, "Manage categories", 600, save_text=None)

    def build(self, body):
        self.table = DataTable(body, [("n", "Category", 170, "w"), ("d", "Description", 230, "w"),
                                      ("c", "Products", 70, "center")], height=7)
        self.table.pack(fill="x")
        self.table.tree.bind("<<TreeviewSelect>>", lambda e: self._fill())
        self.name = Field(body, "Category name")
        self.name.pack(fill="x", pady=(12, 6))
        self.desc = Field(body, "Description (optional)")
        self.desc.pack(fill="x")
        row = tk.Frame(body, bg="white")
        row.pack(fill="x", pady=(12, 0))
        Btn(row, "Add new", self.add).pack(side="left")
        Btn(row, "Save changes to selected", self.save_selected, "secondary").pack(side="left", padx=8)
        Btn(row, "Delete selected", self.delete, "danger").pack(side="right")
        self.reload()

    def reload(self):
        self.rows = {str(c["category_id"]): c for c in self.ctrl.list_categories()}
        self.table.load([(cid, (c["category_name"], c["description"] or "", c["product_count"]), None)
                         for cid, c in self.rows.items()])
        self.on_done()

    def _fill(self):
        row = self.rows.get(self.table.selected())
        if row:
            self.name.set(row["category_name"])
            self.desc.set(row["description"])

    def add(self):
        self.ctrl.save_category(None, self.name.get(), self.desc.get())
        self.name.clear()
        self.desc.clear()
        self.reload()

    def save_selected(self):
        sel = self.table.selected()
        if not sel:
            raise_info(self, "Select a category in the table first.")
            return
        self.ctrl.save_category(int(sel), self.name.get(), self.desc.get())
        self.reload()

    def delete(self):
        sel = self.table.selected()
        if not sel:
            raise_info(self, "Select a category in the table first.")
            return
        if messagebox.askyesno("Delete category", f"Delete '{self.rows[sel]['category_name']}'?", parent=self):
            self.ctrl.delete_category(int(sel))
            self.name.clear()
            self.desc.clear()
            self.reload()


def raise_info(parent, text):
    messagebox.showinfo("Inventoria", text, parent=parent)


class ProductsPage(Page):
    title = "Products"

    def get_subtitle(self):
        if self.app.session.has_permission("product.add"):
            return ("Type in the search box to find a product. Select a row, then click Edit or Delete "
                    "(double-click also edits). Use + Add Product for new items.")
        return "Type in the search box to find a product. Only an Admin can add or change products."

    def build(self):
        self.ctrl = ProductController()
        s = self.app.session
        self.can_add, self.can_edit = s.has_permission("product.add"), s.has_permission("product.edit")
        self.can_delete, self.can_cat = s.has_permission("product.delete"), s.has_permission("category.manage")
        if self.can_cat:
            Btn(self.actions, "Categories", self.open_categories, "secondary").pack(side="left", padx=(0, 8))
        if self.can_add:
            Btn(self.actions, "+ Add Product", self.add).pack(side="left")
        self.search = Field(self.body, "Search by product, specification, SKU or category")
        self.search.pack(fill="x")
        self._after = None
        self.search.entry.bind("<KeyRelease>", lambda e: self._debounce())
        bar = tk.Frame(self.body, bg="white")
        bar.pack(fill="x", pady=(10, 8))
        self.count = tk.Label(bar, text="", bg="white", fg=theme.MUTED)
        self.count.pack(side="left")
        self.show_inactive = tk.BooleanVar(value=False)
        if self.can_edit or self.can_delete:
            tk.Checkbutton(bar, text="Show deleted products", variable=self.show_inactive, bg="white",
                           command=self.refresh).pack(side="right", padx=(12, 0))
        if self.can_delete:
            self.delete_btn = Btn(bar, "Delete", self.toggle_active, "danger")
            self.delete_btn.pack(side="right", padx=(8, 0))
        if self.can_edit:
            Btn(bar, "Edit", self.edit, "secondary").pack(side="right")
        self.table = DataTable(self.body, [("id", "ID", 45, "center"), ("sku", "SKU", 90, "w"),
                                           ("name", "Product", 150, "w"), ("spec", "Specification / unit", 190, "w"),
                                           ("cat", "Category", 110, "w"), ("price", "Price", 85, "e"),
                                           ("stock", "Stock", 65, "center"), ("status", "Status", 90, "center")],
                               height=14)
        self.table.pack(fill="both", expand=True)
        if self.can_edit:
            self.table.on_double_click(self.edit)
        self.table.tree.bind("<<TreeviewSelect>>", lambda e: self._sync_button())

    def _debounce(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(250, self.refresh)

    def refresh(self):
        self.rows = {str(r["product_id"]): r for r in
                     self.ctrl.list_products(self.search.get(), self.show_inactive.get())}
        items = []
        for iid, r in self.rows.items():
            status = stock_status(r["stock_quantity"], r["low_stock_threshold"], bool(r["is_active"]))
            tag = "muted" if status == "Inactive" else ("low" if status != "OK" else None)
            items.append((iid, (r["product_id"], r["sku"], r["product_name"],
                                r["specification"] or "Not specified",
                                r["category_name"], money(r["price"]), r["stock_quantity"], status), tag))
        self.table.load(items)
        self.count.config(text=f"{len(items)} product(s)")

    def _sync_button(self):
        row = self.rows.get(self.table.selected())
        if self.can_delete and row:
            restore = not row["is_active"]
            self.delete_btn.config(text="Restore" if restore else "Delete")
            self.delete_btn.set_kind("success" if restore else "danger")

    def _selected(self):
        row = self.rows.get(self.table.selected())
        if row is None:
            raise_info(self, "Please select a product in the table first.")
        return row

    def _categories(self):
        return self.ctrl.list_categories()

    def add(self):
        ProductDialog(self, self.ctrl, self._categories(), self.refresh)

    def edit(self):
        row = self._selected()
        if row:
            ProductDialog(self, self.ctrl, self._categories(), self.refresh, row)

    def toggle_active(self):
        row = self._selected()
        if not row:
            return
        if row["is_active"]:
            if messagebox.askyesno("Delete product",
                                   f"Delete '{row['product_name']}'?\n\nIt will be hidden from stock and sales screens. "
                                   "Its history is kept and you can restore it later.", parent=self):
                self.ctrl.set_product_active(row["product_id"], False)
        else:
            self.ctrl.set_product_active(row["product_id"], True)
        self.refresh()

    def open_categories(self):
        CategoryDialog(self, self.ctrl, lambda: None)
