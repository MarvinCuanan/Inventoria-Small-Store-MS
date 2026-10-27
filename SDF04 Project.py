"""Inventoria Business Management System - start here:  python main.py"""
import logging
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import messagebox

import config
from controllers import AuthController
from core.bootstrap import ensure_admin_exists, ensure_product_specification
from core.errors import AppError
from core.session import SessionManager
from ui import theme


class InventoriaApp:
    def __init__(self, root):
        self.root = root
        self.session = SessionManager.get_instance()
        self.auth = AuthController()
        self.frame = None
        root.report_callback_exception = self.handle_exception
        root.protocol("WM_DELETE_WINDOW", self.quit)

    # ---- start-up ----
    def start(self):
        try:
            ensure_product_specification()
            ensure_admin_exists()
        except AppError as exc:
            messagebox.showerror(config.APP_NAME, str(exc))
            self.root.destroy()
            return False
        self.show_login()
        return True

    # ---- screen switching ----
    def _swap(self, frame):
        if self.frame is not None:
            self.frame.destroy()
        self.frame = frame
        frame.pack(fill="both", expand=True)

    def show_login(self, username=""):
        from ui.auth_views import LoginView
        self._swap(LoginView(self.root, self, username))

    def show_signup(self):
        from ui.auth_views import SignUpView
        self._swap(SignUpView(self.root, self))

    def show_main(self):
        from ui.main_window import MainWindow
        self._swap(MainWindow(self.root, self))

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to log out?"):
            self.auth.logout()
            self.show_login()

    def quit(self):
        if self.session.is_logged_in():
            if not messagebox.askyesno("Exit", "Log out and close Inventoria?"):
                return
            try:
                self.auth.logout()
            except AppError:
                pass
        self.root.destroy()

    # ---- one place that shows every error ----
    def handle_exception(self, exc_type, value, tb):
        try:
            parent = self.root.focus_get() or self.root
            parent = parent.winfo_toplevel()
        except (KeyError, tk.TclError):
            parent = self.root
        if isinstance(value, AppError):
            messagebox.showwarning(config.APP_NAME, str(value), parent=parent)
        else:
            logging.error("Unhandled error", exc_info=(exc_type, value, tb))
            messagebox.showerror(config.APP_NAME, "Something went wrong. Nothing was lost; the details were "
                                 f"saved to {config.LOG_FILE}.\n\n{value}", parent=parent)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[RotatingFileHandler(config.LOG_FILE, maxBytes=1_000_000,
                                      backupCount=5, encoding="utf-8")],
    )
    root = tk.Tk()
    root.title(f"{config.APP_NAME} - {config.APP_SUBTITLE}")
    root.minsize(1000, 640)
    theme.init_theme(root)
    theme.center_window(root, 1140, 700)
    if InventoriaApp(root).start():
        root.mainloop()


if __name__ == "__main__":
    main()
