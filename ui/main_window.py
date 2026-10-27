"""Main window after login: sidebar + top bar + the selected page."""
import tkinter as tk
from tkinter import messagebox

import config
from ui import theme
from ui.auth_views import draw_logo
from ui.page_audit import AuditPage
from ui.page_dashboard import DashboardPage
from ui.page_help import HelpPage
from ui.page_products import ProductsPage
from ui.page_reports import ReportsPage
from ui.page_stock import StockPage
from ui.page_transactions import TransactionsPage
from ui.page_users import UsersPage
from ui.theme import Btn, Dialog, Field

# label, key, page class, permissions (any one is enough), admin-only section?
NAV = [
    ("Dashboard", "dashboard", DashboardPage, ("dashboard.view",), False),
    ("Products", "products", ProductsPage, ("product.view",), False),
    ("Stock", "stock", StockPage, ("stock.in", "stock.out"), False),
    ("Transactions", "transactions", TransactionsPage, ("transaction.view_all", "transaction.view_own"), False),
    ("Reports", "reports", ReportsPage, ("report.view",), False),
    ("Users", "users", UsersPage, ("user.manage",), True),
    ("Audit Log", "audit", AuditPage, ("audit.view",), True),
    ("Help & Guide", "help", HelpPage, (), False),
]


class ChangePasswordDialog(Dialog):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, "Change password", 400, "Change password")

    def build(self, body):
        self.current = Field(body, "Current password", secret=True)
        self.current.pack(fill="x", pady=(0, 10))
        self.new = Field(body, "New password", secret=True)
        self.new.pack(fill="x", pady=(0, 10))
        self.confirm = Field(body, "Confirm new password", secret=True)
        self.confirm.pack(fill="x")
        self.after(100, self.current.focus)

    def on_save(self):
        self.app.auth.change_password(self.current.get(), self.new.get(), self.confirm.get())
        messagebox.showinfo("Password changed", "Your password was updated.", parent=self)
        self.destroy()


class MainWindow(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="white")
        self.app = app
        session = app.session
        self.page = None
        self.nav_labels = {}

        side = tk.Frame(self, bg=theme.NAVY, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        brand = tk.Frame(side, bg=theme.NAVY)
        brand.pack(fill="x", padx=14, pady=(18, 14))
        draw_logo(brand, 30, theme.NAVY).pack(side="left")
        tk.Label(brand, text=config.APP_NAME, bg=theme.NAVY, fg="white", font=theme.font(15, "bold")).pack(side="left", padx=8)

        self.allowed = [n for n in NAV if not n[3] or any(session.has_permission(p) for p in n[3])]
        shown_admin_header = False
        for label, key, _cls, _perm, admin_section in self.allowed:
            if key == "help":
                continue
            if admin_section and not shown_admin_header:
                tk.Label(side, text="ADMINISTRATION", bg=theme.NAVY, fg="#7f93b5", font=theme.font(9, "bold"),
                         anchor="w").pack(fill="x", padx=22, pady=(16, 4))
                shown_admin_header = True
            self.nav_labels[key] = self._nav_item(side, label, lambda k=key: self.show_page(k))
        tk.Frame(side, bg=theme.NAVY).pack(fill="both", expand=True)
        self.nav_labels["help"] = self._nav_item(side, "Help & Guide", lambda: self.show_page("help"))
        self._nav_item(side, "Logout", app.logout).pack_configure(pady=(0, 14))

        right = tk.Frame(self, bg="white")
        right.pack(side="left", fill="both", expand=True)
        top = tk.Frame(right, bg=theme.SOFT, height=46, highlightthickness=1, highlightbackground=theme.BORDER)
        top.pack(fill="x")
        top.pack_propagate(False)
        user = session.current_user
        pw = tk.Label(top, text="Change password", bg=theme.SOFT, fg=theme.BLUE, cursor="hand2", font=theme.font(10, "bold"))
        pw.pack(side="right", padx=18)
        pw.bind("<Button-1>", lambda e: ChangePasswordDialog(self, app))
        username, role = user["username"], user["role"]
        display_name = role if username.casefold() == role.casefold() else username
        identity = display_name if display_name.casefold() == role.casefold() else f"{display_name}  ·  {role}"
        tk.Label(top, text=identity, bg=theme.SOFT, fg=theme.TEXT,
                 font=theme.font(11, "bold")).pack(side="right", padx=8)
        self.container = tk.Frame(right, bg="white")
        self.container.pack(fill="both", expand=True)
        if self.allowed:
            self.show_page(self.allowed[0][1])
        else:
            tk.Label(self.container, text="Your role has no permissions yet.\nAsk the administrator.",
                     bg="white", fg=theme.MUTED, font=theme.font(13)).pack(expand=True)

    def _nav_item(self, parent, text, command):
        item = tk.Label(parent, text=text, bg=theme.NAVY, fg="#cbd5e1", anchor="w", padx=16, pady=9,
                        cursor="hand2", font=theme.font(12))
        item.pack(fill="x", padx=10, pady=1)
        item.bind("<Button-1>", lambda e: command())
        item.bind("<Enter>", lambda e: item.cget("bg") == theme.NAVY and item.config(bg=theme.NAVY_HOVER))
        item.bind("<Leave>", lambda e: item.cget("bg") == theme.NAVY_HOVER and item.config(bg=theme.NAVY))
        return item

    def show_page(self, key):
        entry = next(n for n in self.allowed if n[1] == key)
        if self.page is not None:
            self.page.destroy()
            self.page = None
        for k, label in self.nav_labels.items():
            active = k == key
            label.config(bg=theme.BLUE if active else theme.NAVY, fg="white" if active else "#cbd5e1",
                         font=theme.font(12, "bold" if active else "normal"))
        self.page = entry[2](self.container, self.app)
        self.page.pack(fill="both", expand=True)
