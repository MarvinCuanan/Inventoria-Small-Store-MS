"""Login and Create Account screens (split layout: navy brand panel + white form)."""
import tkinter as tk
from tkinter import messagebox

from ..config import APP_NAME, APP_SUBTITLE
from ..errors import AppError
from ..services import AuthService
from . import theme
from .theme import BLUE, MUTED, NAVY, RED, TEXT, WHITE, font
from .widgets import PlaceholderEntry, draw_logo, make_button


class _AuthView(tk.Frame):
    heading = ""

    def __init__(self, master, app):
        super().__init__(master, bg=WHITE)
        self.app, self.auth = app, AuthService()

        brand = tk.Frame(self, bg=NAVY, width=430)
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)
        center = tk.Frame(brand, bg=NAVY)
        center.place(relx=0.5, rely=0.5, anchor="center")
        draw_logo(center, 72).pack()
        tk.Label(center, text=APP_NAME, bg=NAVY, fg=WHITE, font=font(16, "bold")).pack(pady=(14, 0))
        tk.Label(center, text=APP_SUBTITLE, bg=NAVY, fg="#cbd5e6", font=font(11)).pack()

        side = tk.Frame(self, bg=WHITE)
        side.pack(side="left", fill="both", expand=True)
        form = tk.Frame(side, bg=WHITE)
        form.place(relx=0.5, rely=0.45, anchor="center", width=400)
        tk.Label(form, text=self.heading, bg=WHITE, fg=TEXT, font=font(24, "bold")).pack(anchor="w", pady=(0, 18))
        self.build_form(form)
        self.error = tk.Label(form, text="", bg=WHITE, fg=RED, font=font(9), wraplength=400, justify="left")
        self.error.pack(anchor="w", pady=(10, 0))

    def build_form(self, form):
        raise NotImplementedError

    def show_error(self, message):
        self.error.config(text=message)

    def link(self, parent, prefix, text, command):
        row = tk.Frame(parent, bg=WHITE)
        row.pack(pady=(16, 0))
        tk.Label(row, text=prefix, bg=WHITE, fg=MUTED, font=font(9)).pack(side="left")
        lbl = tk.Label(row, text=text, bg=WHITE, fg=BLUE, font=font(9, "underline"), cursor="hand2")
        lbl.pack(side="left", padx=(3, 0))
        lbl.bind("<Button-1>", lambda _e: command())


class LoginView(_AuthView):
    heading = "Login"

    def __init__(self, master, app, username=""):
        self._prefill = username
        super().__init__(master, app)
        (self.password if self._prefill else self.username).focus()

    def build_form(self, form):
        self.username = PlaceholderEntry(form, "Username")
        self.username.pack(fill="x", pady=(0, 10))
        self.password = PlaceholderEntry(form, "Password", password=True)
        self.password.pack(fill="x", pady=(0, 14))
        if self._prefill:
            self.username.set(self._prefill)
        self.username.on_return(self.password.focus)
        self.password.on_return(self.submit)
        make_button(form, "Login", self.submit, pady=10).pack(fill="x")
        self.link(form, "Don't have an account?", "Create your own account.", self.app.show_register)

    def submit(self):
        self.show_error("")
        try:
            self.auth.login(self.username.get(), self.password.get())
        except AppError as exc:
            self.show_error(str(exc))
            self.password.clear()
            self.password.focus()
            return
        self.app.show_main()


class RegisterView(_AuthView):
    heading = "Create account"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.username.focus()

    def build_form(self, form):
        self.username = PlaceholderEntry(form, "Username")
        self.username.pack(fill="x", pady=(0, 10))
        self.password = PlaceholderEntry(form, "Password", password=True)
        self.password.pack(fill="x", pady=(0, 10))
        self.confirm = PlaceholderEntry(form, "Confirm password", password=True)
        self.confirm.pack(fill="x", pady=(0, 14))
        self.username.on_return(self.password.focus)
        self.password.on_return(self.confirm.focus)
        self.confirm.on_return(self.submit)
        make_button(form, "Create account", self.submit, pady=10).pack(fill="x")
        tk.Label(form, text="Use 3-30 letters, numbers, dots or underscores. Password: 6+ characters.",
                 bg=WHITE, fg=MUTED, font=font(8)).pack(anchor="w", pady=(10, 0))
        self.link(form, "Already have an account?", "Log in.", self.app.show_login)

    def submit(self):
        self.show_error("")
        username = self.username.get().strip()
        try:
            self.auth.register(username, self.password.get(), self.confirm.get())
        except AppError as exc:
            self.show_error(str(exc))
            return
        messagebox.showinfo("Account created", "Your account was created. You can log in now.")
        self.app.show_login(username)
