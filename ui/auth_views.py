"""Login and Create-account screens (split layout from the system design)."""
import tkinter as tk
from tkinter import messagebox

import config
from core.errors import AppError
from ui import theme
from ui.theme import Btn, Field


def _rounded(canvas, x1, y1, x2, y2, r, fill):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    canvas.create_polygon(pts, smooth=True, fill=fill, outline="")


def draw_logo(parent, size, bg):
    """Little blue shop icon."""
    s = size / 78
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0)
    _rounded(c, 0, 0, size, size, 18 * s, theme.BLUE)
    c.create_rectangle(20 * s, 34 * s, 58 * s, 58 * s, fill="white", outline="")
    c.create_polygon(18 * s, 22 * s, 60 * s, 22 * s, 64 * s, 34 * s, 14 * s, 34 * s, fill="#dbeafe", outline="")
    c.create_rectangle(34 * s, 44 * s, 44 * s, 58 * s, fill="#f59e0b", outline="")
    return c


class _AuthFrame(tk.Frame):
    heading = ""

    def __init__(self, parent, app):
        super().__init__(parent, bg="white")
        self.app = app
        self.columnconfigure(0, weight=1, uniform="half")
        self.columnconfigure(1, weight=1, uniform="half")
        self.rowconfigure(0, weight=1)
        left = tk.Frame(self, bg=theme.NAVY)
        left.grid(row=0, column=0, sticky="nsew")
        brand = tk.Frame(left, bg=theme.NAVY)
        brand.place(relx=0.5, rely=0.5, anchor="center")
        draw_logo(brand, 78, theme.NAVY).pack(pady=(0, 10))
        tk.Label(brand, text=config.APP_NAME, bg=theme.NAVY, fg="white", font=theme.font(16, "bold")).pack()
        tk.Label(brand, text=config.APP_SUBTITLE, bg=theme.NAVY, fg="#dbeafe", font=theme.font(12)).pack()
        right = tk.Frame(self, bg=theme.SOFT)
        right.grid(row=0, column=1, sticky="nsew")
        self.form = tk.Frame(right, bg="white", padx=32, pady=30,
                             highlightthickness=1, highlightbackground=theme.BORDER)
        self.form.place(relx=0.5, rely=0.5, anchor="center", width=440)
        tk.Label(self.form, text=self.heading, bg="white", fg=theme.TEXT, font=theme.font(24, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 18))

    def link_row(self, question, link_text, command):
        row = tk.Frame(self.form, bg="white")
        row.pack(pady=(16, 0))
        tk.Label(row, text=question, bg="white", fg=theme.MUTED).pack(side="left")
        link = tk.Label(row, text=link_text, bg="white", fg=theme.BLUE, cursor="hand2",
                        font=theme.font(11, "bold"))
        link.pack(side="left", padx=(4, 0))
        link.bind("<Button-1>", lambda e: command())


class LoginView(_AuthFrame):
    heading = "Login"

    def __init__(self, parent, app, username=""):
        super().__init__(parent, app)
        self.username = Field(self.form, "Username")
        self.username.pack(fill="x", pady=(0, 10))
        self.password = Field(self.form, "Password", secret=True)
        self.password.pack(fill="x", pady=(0, 14))
        Btn(self.form, "Login", self.submit).pack(fill="x", ipady=4)
        actions = tk.Frame(self.form, bg="white")
        actions.pack(fill="x", pady=(12, 0))
        self.action_link(actions, "Forgot password?", self.show_password_help, side="top")
        self.link_row("Don't have an account?", "Create your own account.", app.show_signup)
        self.username.set(username)
        for f in (self.username, self.password):
            f.entry.bind("<Return>", lambda e: self.submit())
        (self.password if username else self.username).focus()

    @staticmethod
    def action_link(parent, text, command, side="left"):
        link = tk.Label(parent, text=text, bg="white", fg=theme.BLUE, cursor="hand2",
                        font=theme.font(10, "bold"))
        link.pack(side=side)
        link.bind("<Button-1>", lambda e: command())

    def show_password_help(self):
        messagebox.showinfo(
            "Forgot password",
            "Ask another Admin to reset your password from Users > Reset password.",
            parent=self,
        )

    def submit(self):
        try:
            self.app.auth.login(self.username.get(), self.password.get())
        except AppError as exc:
            messagebox.showwarning("Login failed", str(exc), parent=self)
            self.password.clear()
            self.password.focus()
            return
        self.app.show_main()

class SignUpView(_AuthFrame):
    heading = "Create account"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.username = Field(self.form, "Username")
        self.username.pack(fill="x", pady=(0, 10))
        self.password = Field(self.form, "Password", secret=True)
        self.password.pack(fill="x", pady=(0, 10))
        self.confirm = Field(self.form, "Confirm password", secret=True)
        self.confirm.pack(fill="x", pady=(0, 6))
        tk.Label(self.form, text="Use 3-30 letters, numbers, . or _ for the username.\n"
                                 f"Password: at least {config.MIN_PASSWORD_LENGTH} characters. "
                                 "New accounts start as Staff.",
                 bg="white", fg=theme.MUTED, font=theme.font(9), justify="left", anchor="w").pack(fill="x", pady=(0, 12))
        Btn(self.form, "Create account", self.submit).pack(fill="x", ipady=4)
        self.link_row("Already have an account?", "Log in.", app.show_login)
        for f in (self.username, self.password, self.confirm):
            f.entry.bind("<Return>", lambda e: self.submit())
        self.username.focus()

    def submit(self):
        try:
            self.app.auth.register(self.username.get(), self.password.get(), self.confirm.get())
        except AppError as exc:
            messagebox.showwarning("Cannot create account", str(exc), parent=self)
            return
        messagebox.showinfo("Account created", "Your account is ready. You can log in now.", parent=self)
        self.app.show_login(self.username.get())
