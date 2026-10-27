"""The signed-in shell: navy sidebar + the page area."""
import tkinter as tk
from tkinter import messagebox

from ..config import APP_NAME
from ..services import AuthService
from ..session import Session
from . import theme
from .dashboard_page import DashboardPage
from .products_page import ProductsPage
from .reports_page import ReportsPage
from .stock_page import StockPage
from .theme import BLUE, NAVY, NAVY_HOVER, WHITE, font
from .transactions_page import TransactionsPage
from .widgets import draw_logo

NAV = [("Dashboard", DashboardPage, "product.view"), ("Products", ProductsPage, "product.view"),
       ("Stock", StockPage, None), ("Transactions", TransactionsPage, "transaction.view"),
       ("Reports", ReportsPage, "report.view")]


class MainView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=WHITE)
        self.app = app
        self.buttons, self.page, self.current = {}, None, None

        side = tk.Frame(self, bg=NAVY, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        brand = tk.Frame(side, bg=NAVY)
        brand.pack(fill="x", padx=14, pady=(18, 18))
        draw_logo(brand, 28).pack(side="left")
        tk.Label(brand, text=APP_NAME, bg=NAVY, fg=WHITE, font=font(13, "bold")).pack(side="left", padx=8)

        navigation = tk.Frame(side, bg=NAVY)
        navigation.pack(fill="x")
        for label, cls, perm in NAV:
            if perm and not Session.can(perm):
                continue
            if label == "Stock" and not (Session.can("stock.add") or Session.can("stock.remove")):
                continue
            self.buttons[label] = self._nav_button(
                navigation, label, lambda c=cls, l=label: self.navigate(l, c))

        user = Session.current()
        account = tk.Frame(side, bg=NAVY_HOVER, padx=12, pady=12)
        account.pack(side="bottom", fill="x", padx=10, pady=(8, 12))
        username = "Admin" if user.username.casefold() == "admin" else user.username
        role_name = user.role_name or ""
        tk.Label(account, text="SIGNED IN AS", bg=NAVY_HOVER, fg="#aebbd0",
                 font=font(8, "bold")).pack(anchor="w")
        tk.Label(account, text=username, bg=NAVY_HOVER, fg=WHITE,
                 font=font(11, "bold")).pack(anchor="w", pady=(3, 0))
        if role_name.casefold() != username.casefold():
            tk.Label(account, text=role_name, bg=NAVY_HOVER, fg="#cbd5e6",
                     font=font(9)).pack(anchor="w", pady=(1, 0))
        tk.Frame(account, bg="#405574", height=1).pack(fill="x", pady=(10, 8))
        tk.Button(account, text="Log out", command=self.logout, anchor="w", relief="flat", bd=0,
                  cursor="hand2", bg=NAVY_HOVER, fg=WHITE, activebackground=NAVY,
                  activeforeground=WHITE, font=font(10), padx=0, pady=3).pack(fill="x")

        self.content = tk.Frame(self, bg=WHITE)
        self.content.pack(side="left", fill="both", expand=True)
        self.navigate("Dashboard", DashboardPage)

    def _nav_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command, anchor="w", relief="flat", bd=0, cursor="hand2",
                        bg=NAVY, fg=WHITE, activebackground=NAVY_HOVER, activeforeground=WHITE,
                        font=font(11), padx=16, pady=9)
        btn.pack(fill="x", padx=8, pady=2)
        btn.bind("<Enter>", lambda _e: btn["bg"] != BLUE and btn.config(bg=NAVY_HOVER))
        btn.bind("<Leave>", lambda _e: btn["bg"] != BLUE and btn.config(bg=NAVY))
        return btn

    def navigate(self, label, cls, *args):
        if self.page is not None:
            self.page.destroy()
        for name, btn in self.buttons.items():
            active = name == label
            btn.config(bg=BLUE if active else NAVY, activebackground=BLUE if active else NAVY_HOVER)
        self.current = label
        self.page = cls(self.content, self, *args)
        self.page.pack(fill="both", expand=True)

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            AuthService().logout()
            self.app.show_login()
