"""Top-level window: switches between the login, register and main views."""
import tkinter as tk

from ..config import APP_NAME, APP_SUBTITLE
from . import theme
from .auth_views import LoginView, RegisterView
from .main_window import MainView


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"{APP_NAME} - {APP_SUBTITLE}")
        theme.apply_theme(root)
        root.minsize(1000, 640)
        theme.center_window(root, 1180, 720)
        self.view = None

    def _swap(self, view_cls, *args):
        if self.view is not None:
            self.view.destroy()
        self.view = view_cls(self.root, self, *args)
        self.view.pack(fill="both", expand=True)

    def show_login(self, username=""):
        self._swap(LoginView, username)

    def show_register(self):
        self._swap(RegisterView)

    def show_main(self):
        self._swap(MainView)
