import tkinter as tk
from tkinter import filedialog, messagebox

from controllers import DatabaseBackupController, UserManagementController
from core.formatting import short_dt
from core.errors import AppError
from ui import theme
from ui.theme import Btn, ComboField, DataTable, Dialog, Field, Page


class UserDialog(Dialog):
    def __init__(self, parent, ctrl, on_done):
        self.ctrl, self.on_done = ctrl, on_done
        super().__init__(parent, "Add user", 460)

    def build(self, body):
        self.username = Field(body, "Username")
        self.username.pack(fill="x", pady=(0, 8))
        self.full_name = Field(body, "Full name")
        self.full_name.pack(fill="x", pady=(0, 8))
        row = tk.Frame(body, bg="white")
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure((0, 1), weight=1, uniform="r")
        self.email = Field(row, "Email (optional)")
        self.email.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.contact = Field(row, "Contact no. (optional)")
        self.contact.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.role = ComboField(body, "Role", [(r["role_name"], r["role_id"]) for r in self.ctrl.list_roles()])
        self.role.pack(fill="x", pady=(0, 8))
        self.role.select_value(self.ctrl.roles.find_by_name("Staff")["role_id"])
        self.password = Field(body, "Password", secret=True)
        self.password.pack(fill="x", pady=(0, 8))
        self.confirm = Field(body, "Confirm password", secret=True)
        self.confirm.pack(fill="x")
        self.after(100, self.username.focus)

    def on_save(self):
        self.ctrl.create_user(self.username.get(), self.password.get(), self.confirm.get(), self.role.value(),
                              self.full_name.get(), self.email.get(), self.contact.get())
        self.destroy()
        self.on_done()


class RoleDialog(Dialog):
    def __init__(self, parent, ctrl, user, on_done):
        self.ctrl, self.user, self.on_done = ctrl, user, on_done
        super().__init__(parent, "Change role", 380)

    def build(self, body):
        tk.Label(body, text=f"User: {self.user['username']}", bg="white", fg=theme.TEXT,
                 font=theme.font(12, "bold")).pack(anchor="w", pady=(0, 10))
        self.role = ComboField(body, "New role", [(r["role_name"], r["role_id"]) for r in self.ctrl.list_roles()])
        self.role.pack(fill="x")
        self.role.select_value(self.user["role_id"])

    def on_save(self):
        self.ctrl.change_role(self.user["user_id"], self.role.value())
        self.destroy()
        self.on_done()


class ResetPasswordDialog(Dialog):
    def __init__(self, parent, ctrl, user):
        self.ctrl, self.user = ctrl, user
        super().__init__(parent, "Reset password", 400, "Reset password")

    def build(self, body):
        tk.Label(body, text=f"Set a new password for {self.user['username']}", bg="white", fg=theme.TEXT,
                 font=theme.font(12, "bold")).pack(anchor="w", pady=(0, 10))
        self.password = Field(body, "New password", secret=True)
        self.password.pack(fill="x", pady=(0, 8))
        self.confirm = Field(body, "Confirm new password", secret=True)
        self.confirm.pack(fill="x")

    def on_save(self):
        self.ctrl.reset_password(self.user["user_id"], self.password.get(), self.confirm.get())
        messagebox.showinfo("Done", "Password updated. Share it with the user through a secure channel.", parent=self)
        self.destroy()


class PermissionsDialog(Dialog):
    """Tick what each role may do. Changes apply the next time those users log in."""
    LOCKED = ("user.manage", "audit.view", "dashboard.view")

    def __init__(self, parent, ctrl):
        self.ctrl = ctrl
        super().__init__(parent, "Role permissions", 480)

    def build(self, body):
        roles = self.ctrl.list_roles()
        self.role = ComboField(body, "Role", [(r["role_name"], r["role_id"]) for r in roles])
        self.role.pack(fill="x")
        self.role.select_first()
        self.role.on_change(self.load)
        self.box = tk.Frame(body, bg="white")
        self.box.pack(fill="x", pady=(12, 0))
        self.checks = {}
        self.load()

    def load(self):
        for child in self.box.winfo_children():
            child.destroy()
        perms, granted = self.ctrl.permission_matrix(self.role.value())
        is_admin = self.role.text() == "Admin"
        self.checks = {}
        for p in perms:
            var = tk.BooleanVar(value=p["permission_id"] in granted)
            locked = is_admin and p["permission_name"] in self.LOCKED
            tk.Checkbutton(self.box, text=p["description"], variable=var, bg="white", anchor="w",
                           state="disabled" if locked else "normal", font=theme.font(11)).pack(fill="x")
            self.checks[p["permission_id"]] = var

    def on_save(self):
        self.ctrl.save_role_permissions(self.role.value(), [pid for pid, v in self.checks.items() if v.get()])
        messagebox.showinfo("Saved", "Permissions saved. Users get the change the next time they log in.", parent=self)
        self.destroy()


class DatabaseBackupDialog(Dialog):
    def __init__(self, parent):
        self.backups = DatabaseBackupController()
        self.app = parent.app
        super().__init__(parent, "Database backup & restore", 500, save_text=None)

    def build(self, body):
        tk.Label(body, text="Protect your inventory data", bg="white", fg=theme.TEXT,
                 font=theme.font(14, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(body, text="A backup includes products, stock, transactions, users, and audit history. "
                            "Store backup files somewhere secure because they contain password hashes "
                            "and business data.",
                 bg="white", fg=theme.MUTED, wraplength=440, justify="left").pack(anchor="w", pady=(0, 16))
        Btn(body, "Create backup", self.create_backup).pack(fill="x", pady=(0, 8))
        Btn(body, "Restore from backup", self.restore_backup, "secondary").pack(fill="x")

    def create_backup(self):
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json", filetypes=[("Inventoria backup", "*.json")],
            initialfile="inventoria_backup.json")
        if not path:
            return
        try:
            self.backups.create_backup(path)
        except (AppError, OSError) as exc:
            messagebox.showerror("Backup failed", str(exc), parent=self)
            return
        messagebox.showinfo("Backup complete", "Your database backup was saved.", parent=self)

    def restore_backup(self):
        path = filedialog.askopenfilename(
            parent=self, filetypes=[("Inventoria backup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        if not messagebox.askyesno(
                "Replace current database?",
                "Restoring replaces all current products, users, transactions, and audit history "
                "with the backup data. This cannot be undone. Continue?",
                parent=self):
            return
        try:
            self.backups.restore_backup(path)
        except (AppError, OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror("Restore failed", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Restore complete",
            "The database was restored. Please sign in using an account from the restored backup.",
            parent=self,
        )
        self.destroy()
        self.app.session.end()
        self.app.show_login()


class UsersPage(Page):
    title = "User Management"
    subtitle = "Add accounts, change roles, deactivate people who left, and reset forgotten passwords."

    def build(self):
        self.ctrl = UserManagementController()
        Btn(self.actions, "Backup / Restore", lambda: DatabaseBackupDialog(self), "secondary").pack(
            side="left", padx=(0, 8))
        Btn(self.actions, "Role permissions", lambda: PermissionsDialog(self, self.ctrl), "secondary").pack(side="left", padx=(0, 8))
        Btn(self.actions, "+ Add User", lambda: UserDialog(self, self.ctrl, self.refresh)).pack(side="left")
        bar = tk.Frame(self.body, bg="white")
        bar.pack(fill="x", pady=(0, 8))
        tk.Label(bar, text="Select a user, then choose an action:", bg="white", fg=theme.MUTED).pack(side="left")
        Btn(bar, "Reset password", self.reset, "secondary").pack(side="right")
        self.toggle_btn = Btn(bar, "Deactivate", self.toggle, "danger")
        self.toggle_btn.pack(side="right", padx=8)
        Btn(bar, "Change role", self.change_role, "secondary").pack(side="right")
        self.table = DataTable(self.body, [("id", "ID", 50, "center"), ("u", "Username", 130, "w"),
                                           ("n", "Full name", 190, "w"), ("r", "Role", 80, "center"),
                                           ("s", "Status", 80, "center"), ("l", "Last login", 130, "w"),
                                           ("c", "Created", 130, "w")], height=14)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", lambda e: self._sync())

    def refresh(self):
        self.rows = {str(u["user_id"]): u for u in self.ctrl.list_users()}
        self.table.load([(uid, (u["user_id"], u["username"], u["full_name"] or "", u["role_name"],
                                "Active" if u["is_active"] else "Inactive", short_dt(u["last_login_at"]),
                                short_dt(u["created_at"])), None if u["is_active"] else "muted")
                         for uid, u in self.rows.items()])

    def _sync(self):
        u = self.rows.get(self.table.selected())
        if u:
            on = bool(u["is_active"])
            self.toggle_btn.config(text="Deactivate" if on else "Activate")
            self.toggle_btn.set_kind("danger" if on else "success")

    def _selected(self):
        u = self.rows.get(self.table.selected())
        if u is None:
            messagebox.showinfo("Inventoria", "Please select a user in the table first.", parent=self)
        return u

    def change_role(self):
        u = self._selected()
        if u:
            RoleDialog(self, self.ctrl, u, self.refresh)

    def toggle(self):
        u = self._selected()
        if not u:
            return
        turning_off = bool(u["is_active"])
        if turning_off and not messagebox.askyesno(
                "Deactivate", f"Deactivate '{u['username']}'? They will no longer be able to log in.", parent=self):
            return
        self.ctrl.set_active(u["user_id"], not turning_off)
        self.refresh()

    def reset(self):
        u = self._selected()
        if u:
            ResetPasswordDialog(self, self.ctrl, u)
