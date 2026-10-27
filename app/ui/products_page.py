import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from ..config import DEFAULT_LOW_STOCK_THRESHOLD
from ..errors import AppError
from ..services import InventoryService
from ..session import Session
from .pages import BasePage
from .theme import MUTED, RED, TEXT, WHITE, font
from .widgets import ModalDialog, PlaceholderEntry, fill_table, make_button, make_table

ACTION_COL = "#6"


class ProductDialog(ModalDialog):
    """Add / Edit product form. ``on_save`` raises AppError for bad input (shown inline)."""

    def __init__(self, master, product, categories, on_save):
        editing = product is not None
        super().__init__(master, "Edit Product" if editing else "Add Product", 440, 540)
        self.on_save = on_save
        b = self.body
        tk.Label(b, text="Edit Product" if editing else "Add Product", bg=WHITE, fg=TEXT,
                 font=font(15, "bold")).pack(anchor="w", pady=(0, 12))

        def field(label):
            tk.Label(b, text=label, bg=WHITE, fg=MUTED, font=font(9)).pack(anchor="w", pady=(6, 2))

        field("Product name")
        self.name = PlaceholderEntry(b, "e.g. Rice (1kg)")
        self.name.pack(fill="x")
        field("Category (pick one or type a new one)")
        self.category = ttk.Combobox(b, values=[c["category_name"] for c in categories], font=font(10))
        self.category.pack(fill="x", ipady=3)
        field("Price (\u20b1)")
        self.price = PlaceholderEntry(b, "e.g. 45.00")
        self.price.pack(fill="x")
        field("Low-stock alert level")
        self.threshold = PlaceholderEntry(b, str(DEFAULT_LOW_STOCK_THRESHOLD))
        self.threshold.pack(fill="x")
        if editing:
            field("Current stock")
            tk.Label(b, text=f"{product['stock_quantity']}  \u2014 change it from the Stock page",
                     bg=WHITE, fg=TEXT, font=font(10)).pack(anchor="w")
            self.name.set(product["product_name"])
            self.category.set(product["category_name"] or "")
            self.price.set(f"{product['price']:.2f}")
            self.threshold.set(str(product["low_stock_threshold"]))
            self.stock = None
        else:
            field("Initial stock")
            self.stock = PlaceholderEntry(b, "0")
            self.stock.pack(fill="x")
        self.error = tk.Label(b, text="", bg=WHITE, fg=RED, font=font(9), wraplength=390, justify="left")
        self.error.pack(anchor="w", pady=(10, 0))
        buttons = tk.Frame(b, bg=WHITE)
        buttons.pack(fill="x", pady=(8, 0))
        make_button(buttons, "Save", self.save).pack(side="right")
        make_button(buttons, "Cancel", self.destroy, kind="secondary").pack(side="right", padx=8)
        self.name.on_return(self.save)
        self.name.focus()
        self.go_modal()

    def save(self):
        values = {"name": self.name.get(), "category": self.category.get(),
                  "price": self.price.get(), "threshold": self.threshold.get()}
        if self.stock is not None:
            values["stock"] = self.stock.get()
        try:
            self.on_save(values)
        except AppError as exc:
            self.error.config(text=str(exc))
            return
        self.destroy()


class ProductsPage(BasePage):
    title = "Products"

    def __init__(self, master, main):
        super().__init__(master, main)
        self.service = InventoryService()
        self.products = {}
        self._after = None
        if Session.can("product.add"):
            make_button(self.header_right, "+ Add Product", self.add_product).pack()

        self.search = PlaceholderEntry(self.body, "Search product...")
        search_bar = tk.Frame(self.body, bg=WHITE)
        search_bar.pack(fill="x", pady=(0, 10))
        self.search.pack(in_=search_bar, side="left", fill="x", expand=True)
        self.search.entry.bind("<KeyRelease>", self._debounce)
        self.search.on_return(self.reload)
        self.search.entry.bind("<Escape>", self.clear_search)
        make_button(search_bar, "Clear", self.clear_search, kind="secondary").pack(side="left", padx=(8, 0))

        box, self.tree = make_table(self.body, [("id", "ID", 60, "w"), ("name", "Product Name", 260, "w"),
                                                ("category", "Category", 150, "w"), ("price", "Price", 100, "w"),
                                                ("stock", "Stock", 80, "w"), ("action", "Action", 150, "w")])
        box.pack(fill="both", expand=True)
        self.count = tk.Label(self.body, text="", bg=WHITE, fg=MUTED, font=font(9))
        self.count.pack(anchor="w", pady=(6, 0))
        self._text_font = tkfont.Font(family="Segoe UI", size=10)
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())
        self.reload()

    # ---- data ----
    def _debounce(self, _e=None):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(250, self.reload)

    def clear_search(self, _event=None):
        if self._after:
            self.after_cancel(self._after)
            self._after = None
        self.search.clear()
        self.reload()
        return "break"

    def reload(self):
        self._after = None
        try:
            rows = self.service.list_products(self.search.get())
        except AppError as exc:
            messagebox.showerror("Products", str(exc))
            return
        self.products = {str(r["product_id"]): r for r in rows}
        can_delete = Session.can("product.delete")
        action = "[Edit]  [Delete]" if can_delete else "[Edit]"
        values = [(r["product_id"], r["product_name"], r["category_name"] or "\u2014",
                   f"\u20b1{r['price']:,.2f}", r["stock_quantity"], action) for r in rows]
        tags = [("low",) if r["stock_quantity"] <= r["low_stock_threshold"] else () for r in rows]
        fill_table(self.tree, values, tags)
        if self.search.get():
            low_count = sum(r["stock_quantity"] <= r["low_stock_threshold"] for r in rows)
            self.count.config(text=(f"{len(rows)} product(s) found · {low_count} at/below alert level"
                                    if rows else "No products found. Press Escape or Clear to show all products."))
        else:
            low_count = sum(r["stock_quantity"] <= r["low_stock_threshold"] for r in rows)
            self.count.config(text=f"{len(rows)} product(s) · {low_count} at/below alert level. "
                              "Rows in red need attention."
                              if rows else "No products yet. Click \"+ Add Product\" to create one.")

    def _product_of(self, iid):
        pid = str(self.tree.item(iid, "values")[0])
        return self.products.get(pid)

    # ---- mouse handling for the [Edit] [Delete] column ----
    def _action_at(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell" or self.tree.identify_column(event.x) != ACTION_COL:
            return None, None
        iid = self.tree.identify_row(event.y)
        if not iid:
            return None, None
        box = self.tree.bbox(iid, ACTION_COL)
        if not box:
            return None, None
        x = box[0]
        edit_width = self._text_font.measure("[Edit]") + 10
        if event.x - x <= edit_width:
            return iid, "edit"
        return (iid, "delete") if Session.can("product.delete") else (iid, None)

    def _on_motion(self, event):
        _iid, action = self._action_at(event)
        self.tree.config(cursor="hand2" if action else "")

    def _on_click(self, event):
        iid, action = self._action_at(event)
        if action == "edit":
            self.edit_product(self._product_of(iid))
        elif action == "delete":
            self.delete_product(self._product_of(iid))

    def _on_double(self, event):
        iid = self.tree.identify_row(event.y)
        if iid and self.tree.identify_column(event.x) != ACTION_COL:
            self.edit_product(self._product_of(iid))

    # ---- actions ----
    def add_product(self):
        try:
            categories = self.service.categories_list()
        except AppError as exc:
            messagebox.showerror("Add product", str(exc))
            return

        def save(v):
            self.service.add_product(v["name"], v["category"], v["price"], v["stock"], v["threshold"])
        ProductDialog(self, None, categories, save)
        self.reload()

    def edit_product(self, product):
        if product is None or not Session.can("product.edit"):
            return
        try:
            categories = self.service.categories_list()
        except AppError as exc:
            messagebox.showerror("Edit product", str(exc))
            return

        def save(v):
            self.service.update_product(product["product_id"], v["name"], v["category"], v["price"], v["threshold"])
        ProductDialog(self, product, categories, save)
        self.reload()

    def delete_selected(self):
        sel = self.tree.selection()
        if sel:
            self.delete_product(self._product_of(sel[0]))

    def delete_product(self, product):
        if product is None or not Session.can("product.delete"):
            return
        if not messagebox.askyesno("Delete product",
                                   f"Delete \"{product['product_name']}\"?\n\nIts transaction history is kept.",
                                   icon="warning"):
            return
        try:
            self.service.delete_product(product["product_id"])
        except AppError as exc:
            messagebox.showerror("Delete product", str(exc))
        self.reload()
