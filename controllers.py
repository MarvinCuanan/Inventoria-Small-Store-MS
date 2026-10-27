"""Controllers - the business rules.  Every method checks the caller's permission first, validates
input, talks to the repositories, and writes an audit-log entry for anything that changes data.

Screens never touch SQL; they only call these methods and show the result (or the AppError message).
"""
from __future__ import annotations

import time
import uuid
from datetime import date

import config
from core.audit import AuditLogger
from core.database_backup import DatabaseBackup
from core.database import DatabaseManager
from core.domain import PasswordCredentials, StockLevel
from core.errors import AppError
from core.formatting import stock_status, write_csv
from core.security import hash_password
from core.session import SessionManager
from core.validator import Validator
from repositories import (AuditLogRepository, CategoryRepository, ProductRepository, RoleRepository,
                          TransactionRepository, UserRepository)

PASSWORD_HINT = f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters."
USERNAME_HINT = "Username must be 3-30 characters: letters, numbers, dot or underscore."


class BaseController:
    def __init__(self):
        self.session = SessionManager.get_instance()
        self.db = DatabaseManager.get_instance()
        self.audit = AuditLogger()

    def require(self, permission: str, action: str = "do this") -> None:
        self.session.require(permission, action)

    @property
    def me(self) -> dict:
        return self.session.current_user

    @staticmethod
    def date_range(from_text, to_text, required=False):
        """Validate two 'YYYY-MM-DD' strings -> (from_iso | None, to_iso | None)."""
        parsed = []
        for text in (from_text, to_text):
            text = (text or "").strip()
            if not text:
                parsed.append(None)
                continue
            value = Validator.parse_date(text)
            if value is None:
                raise AppError(f"'{text}' is not a valid date. Use YYYY-MM-DD, for example "
                               f"{date.today().isoformat()}.")
            parsed.append(value)
        if required and (parsed[0] is None or parsed[1] is None):
            raise AppError("Please enter both dates (YYYY-MM-DD).")
        if not Validator.is_valid_date_range(parsed[0], parsed[1]):
            raise AppError("The 'From' date cannot be later than the 'To' date.")
        return tuple(d.isoformat() if d else None for d in parsed)

    @staticmethod
    def check_password(password: str, confirm: str) -> None:
        if len(password) < config.MIN_PASSWORD_LENGTH:
            raise AppError(PASSWORD_HINT)
        if not Validator.passwords_match(password, confirm):
            raise AppError("The passwords do not match.")


# ====================================================================== 1.0 Authenticate
class AuthController(BaseController):
    _failures: dict[str, list[float]] = {}

    def __init__(self):
        super().__init__()
        self.users, self.roles = UserRepository(), RoleRepository()

    def register(self, username, password, confirm):
        """Self sign-up. New accounts are always Staff; an Admin can promote them later."""
        username = (username or "").strip()
        if not Validator.is_valid_username(username):
            raise AppError(USERNAME_HINT)
        self.check_password(password, confirm)
        if self.users.exists_by_username(username):
            raise AppError("That username is already taken. Please choose another.")
        staff = self.roles.find_by_name("Staff")
        if staff is None:
            raise AppError("The 'Staff' role is missing. Re-run setup_database.py.")
        with self.db.transaction() as cur:
            uid = self.users.create(username, hash_password(password), staff["role_id"], username, cursor=cur)
            self.audit.log("INSERT", "users", uid, None,
                           {"username": username, "role": "Staff", "source": "self sign-up"},
                           cursor=cur, user_id=uid)

    def login(self, username, password):
        username = (username or "").strip()
        if not username or not password:
            raise AppError("Please enter your username and password.")
        key = username.lower()
        self._check_lockout(key)
        user = self.users.find_by_username(username)
        if user is None or not PasswordCredentials(user["password_hash"]).verifies(password):
            self._failures.setdefault(key, []).append(time.time())
            raise AppError("Invalid username or password.")
        if not user["is_active"]:
            raise AppError("This account is deactivated. Please contact the administrator.")
        self._failures.pop(key, None)
        permissions = self.roles.find_permissions(user["role_id"])
        self.session.start({"user_id": user["user_id"], "username": user["username"],
                            "full_name": user["full_name"] or user["username"],
                            "role": user["role_name"], "role_id": user["role_id"]}, permissions)
        self.users.touch_login(user["user_id"])
        self.audit.log("LOGIN", "users", user["user_id"], user_id=user["user_id"])

    def _check_lockout(self, key):
        now = time.time()
        recent = [t for t in self._failures.get(key, []) if now - t < config.LOCKOUT_SECONDS]
        self._failures[key] = recent
        if len(recent) >= config.MAX_LOGIN_ATTEMPTS:
            wait = int(config.LOCKOUT_SECONDS - (now - recent[0])) + 1
            raise AppError(f"Too many failed attempts. Please wait {wait} seconds and try again.")

    def logout(self):
        if self.session.is_logged_in():
            self.audit.log("LOGOUT", "users", self.me["user_id"])
            self.session.end()

    def change_password(self, current, new, confirm):
        user = self.users.find_by_id(self.me["user_id"])
        if not PasswordCredentials(user["password_hash"]).verifies(current or ""):
            raise AppError("Your current password is incorrect.")
        self.check_password(new, confirm)
        with self.db.transaction() as cur:
            self.users.set_password(user["user_id"], hash_password(new), cur)
            self.audit.log("UPDATE", "users", user["user_id"], None, {"password": "changed by user"}, cursor=cur)

    def change_password_from_login(self, username, current, new, confirm):
        username = (username or "").strip()
        if not username:
            raise AppError("Enter your username.")
        key = username.lower()
        self._check_lockout(key)
        user = self.users.find_by_username(username)
        if (user is None or not user["is_active"]
                or not PasswordCredentials(user["password_hash"]).verifies(current or "")):
            self._failures.setdefault(key, []).append(time.time())
            raise AppError("The username or current password is incorrect.")
        self.check_password(new, confirm)
        with self.db.transaction() as cur:
            self.users.set_password(user["user_id"], hash_password(new), cur)
            self.audit.log("UPDATE", "users", user["user_id"], None,
                           {"password": "changed before login"}, cursor=cur, user_id=user["user_id"])
        self._failures.pop(key, None)


# ====================================================================== 6.0 Dashboard
class DashboardController(BaseController):
    def __init__(self):
        super().__init__()
        self.products, self.transactions = ProductRepository(), TransactionRepository()

    def get_summary(self) -> dict:
        self.require("dashboard.view", "view the dashboard")
        low = self.products.find_low_stock()
        return {"total_products": self.products.count_active(),
                "total_stock": self.products.sum_stock(),
                "low_stock": len(low),
                "today_transactions": self.transactions.count_by_date(date.today().isoformat()),
                "low_items": low}


# ====================================================================== 3.x Inventory records
class ProductController(BaseController):
    def __init__(self):
        super().__init__()
        self.products, self.categories = ProductRepository(), CategoryRepository()
        self.transactions = TransactionRepository()

    # ---- read ----
    def list_products(self, keyword="", include_inactive=False):
        self.require("product.view", "view products")
        return self.products.search(keyword or "", include_inactive)

    def list_categories(self):
        self.require("product.view", "view categories")
        return self.categories.find_all_with_counts()

    # ---- 3.1 categories ----
    def save_category(self, category_id, name, description):
        self.require("category.manage", "manage categories")
        name, description = (name or "").strip(), (description or "").strip()
        if not name:
            raise AppError("Category name is required.")
        if len(name) > 100 or len(description) > 255:
            raise AppError("Category text is too long.")
        if self.categories.exists_by_name(name, category_id):
            raise AppError("A category with that name already exists.")
        with self.db.transaction() as cur:
            if category_id:
                old = self.categories.find_by_id(category_id, cur)
                self.categories.update(category_id, name, description, cur)
                self.audit.log("UPDATE", "categories", category_id,
                               {"category_name": old["category_name"], "description": old["description"]},
                               {"category_name": name, "description": description}, cursor=cur)
            else:
                new_id = self.categories.create(name, description, cur)
                self.audit.log("INSERT", "categories", new_id, None,
                               {"category_name": name, "description": description}, cursor=cur)

    def delete_category(self, category_id):
        self.require("category.manage", "manage categories")
        row = next((c for c in self.categories.find_all_with_counts() if c["category_id"] == category_id), None)
        if row is None:
            raise AppError("Category not found.")
        if row["product_count"]:
            raise AppError(f"'{row['category_name']}' still has {row['product_count']} product(s). "
                           "Move them to another category first.")
        with self.db.transaction() as cur:
            self.categories.delete(category_id, cur)
            self.audit.log("DELETE", "categories", category_id, {"category_name": row["category_name"]}, cursor=cur)

    # ---- 3.2 add / 3.3 update / 3.4 deactivate ----
    def _clean(self, data: dict, editing_id=None) -> dict:
        name = (data.get("name") or "").strip()
        specification = (data.get("specification") or "").strip()
        sku = (data.get("sku") or "").strip().upper()
        if not name:
            raise AppError("Product name is required.")
        if len(name) > 100:
            raise AppError("Product name must be 100 characters or fewer.")
        if not specification:
            raise AppError("Product specification is required. Enter the package or selling unit, "
                           "for example '1 sack (50 kg)' or '1 bottle (500 ml)'.")
        if len(specification) > 255:
            raise AppError("Product specification must be 255 characters or fewer.")
        if len(sku) > 50:
            raise AppError("SKU must be 50 characters or fewer.")
        if not data.get("category_id"):
            raise AppError("Please choose a category.")
        price = Validator.parse_price(data.get("price"))
        if price is None:
            raise AppError("Price must be a valid number (0 or more), for example 45 or 45.50.")
        threshold = Validator.parse_int(data.get("threshold"), 0, 1_000_000)
        if threshold is None:
            raise AppError("Low-stock alert level must be a whole number (0 or more).")
        if self.products.exists_by_name(name, specification, editing_id):
            raise AppError(f"A product named '{name}' with specification '{specification}' already exists.")
        if sku and self.products.exists_sku(sku, editing_id):
            raise AppError(f"SKU '{sku}' is already used by another product.")
        return {"name": name, "specification": specification, "sku": sku,
                "category_id": data["category_id"], "price": price,
                "threshold": threshold}

    def add_product(self, data: dict):
        self.require("product.add", "add products")
        c = self._clean(data)
        stock = Validator.parse_int(data.get("stock") or "0", 0, config.MAX_STOCK_MOVEMENT * 10)
        if stock is None:
            raise AppError("Opening stock must be a whole number (0 or more).")
        with self.db.transaction() as cur:
            pid = self.products.create(c["sku"] or uuid.uuid4().hex[:12].upper(), c["name"],
                                       c["specification"], c["category_id"], c["price"], stock,
                                       c["threshold"], cur)
            if not c["sku"]:
                c["sku"] = f"SKU{pid:05d}"
                self.products.set_sku(pid, c["sku"], cur)
            if stock > 0:   # keep the stock ledger complete
                self.transactions.create(pid, self.me["user_id"], c["price"], "IN", stock, "Opening stock", cur)
            self.audit.log("INSERT", "products", pid, None,
                           {"sku": c["sku"], "product_name": c["name"], "specification": c["specification"],
                            "price": c["price"],
                            "stock_quantity": stock, "low_stock_threshold": c["threshold"]}, cursor=cur)
        return pid

    def edit_product(self, product_id, data: dict):
        """Stock level is NOT editable here - it only changes through Stock In/Out so history stays correct."""
        self.require("product.edit", "edit products")
        c = self._clean(data, product_id)
        is_active = bool(data.get("is_active", True))
        with self.db.transaction() as cur:
            old = self.products.find_by_id(product_id, cur, for_update=True)
            if old is None:
                raise AppError("That product no longer exists.")
            self.products.update(product_id, c["sku"] or old["sku"], c["name"], c["specification"],
                                 c["category_id"], c["price"], c["threshold"], is_active, cur)
            self.audit.log("UPDATE", "products", product_id,
                           {"sku": old["sku"], "product_name": old["product_name"],
                            "specification": old["specification"], "category_id": old["category_id"],
                            "price": old["price"], "low_stock_threshold": old["low_stock_threshold"],
                            "is_active": old["is_active"]},
                           {"sku": c["sku"] or old["sku"], "product_name": c["name"],
                            "specification": c["specification"], "category_id": c["category_id"],
                            "price": c["price"], "low_stock_threshold": c["threshold"],
                            "is_active": int(is_active)}, cursor=cur)

    def set_product_active(self, product_id, active: bool):
        """Soft delete / restore: the row stays so old transactions keep their product name."""
        self.require("product.delete", "delete products")
        with self.db.transaction() as cur:
            old = self.products.find_by_id(product_id, cur, for_update=True)
            if old is None:
                raise AppError("That product no longer exists.")
            self.products.set_active(product_id, active, cur)
            self.audit.log("UPDATE" if active else "DELETE", "products", product_id,
                           {"product_name": old["product_name"], "specification": old["specification"],
                            "is_active": old["is_active"]},
                           {"is_active": int(active)}, cursor=cur)


# ====================================================================== 3.6 / 3.7 Stock in & out
class StockController(BaseController):
    def __init__(self):
        super().__init__()
        self.products, self.transactions = ProductRepository(), TransactionRepository()

    def search_products(self, keyword=""):
        if not (self.session.has_permission("stock.in") or self.session.has_permission("stock.out")):
            raise AppError("Your role is not allowed to manage stock.")
        return self.products.search(keyword or "", include_inactive=False)

    def submit(self, product_id, quantity_text, mode, remarks=""):
        """mode = 'IN' (add stock) or 'OUT' (remove stock). Atomic: stock + transaction + audit together."""
        if mode not in ("IN", "OUT"):
            raise AppError("Unknown stock action.")
        self.require("stock.in" if mode == "IN" else "stock.out",
                     "add stock" if mode == "IN" else "remove stock")
        if not product_id:
            raise AppError("Please choose a product.")
        qty = Validator.parse_int(quantity_text, 1, config.MAX_STOCK_MOVEMENT)
        if qty is None:
            raise AppError(f"Quantity must be a whole number from 1 to {config.MAX_STOCK_MOVEMENT:,}.")
        remarks = (remarks or "").strip()[:255]
        with self.db.transaction() as cur:
            product = self.products.find_by_id(product_id, cur, for_update=True)   # row lock = no double-selling
            if product is None or not product["is_active"]:
                raise AppError("This product is no longer available.")
            old = product["stock_quantity"]
            if mode == "OUT" and qty > old:
                raise AppError(f"Insufficient stock. Only {old} unit(s) of '{product['product_name']} "
                               f"({product['specification']})' left.")
            level = StockLevel(old)
            new = level.increase(qty) if mode == "IN" else level.decrease(qty)
            self.products.update_stock(product_id, new, cur)
            tid = self.transactions.create(product_id, self.me["user_id"], product["price"], mode, qty, remarks, cur)
            self.audit.log("UPDATE", "products", product_id, {"stock_quantity": old},
                           {"stock_quantity": new, "transaction_id": tid, "type": mode, "quantity": qty}, cursor=cur)
        return {"name": product["product_name"], "specification": product["specification"],
                "old": old, "new": new, "qty": qty, "mode": mode,
                "low": new <= product["low_stock_threshold"]}


# ====================================================================== 4.0 View transactions
class TransactionController(BaseController):
    def __init__(self):
        super().__init__()
        self.transactions = TransactionRepository()
        self.users = UserRepository()

    def list_users(self):
        self.require("transaction.view_all", "view everyone's transactions")
        return self.users.find_all_with_roles()

    def list_transactions(self, tx_type=None, date_from="", date_to="", keyword="", user_id=None):
        """Admin: everything (optionally one user).  Staff: only their own records."""
        can_all = self.session.has_permission("transaction.view_all")
        if not (can_all or self.session.has_permission("transaction.view_own")):
            raise AppError("Your role is not allowed to view transactions.")
        d_from, d_to = self.date_range(date_from, date_to)
        if not can_all:
            user_id = self.me["user_id"]
        rows = self.transactions.find_by_filter(tx_type, d_from, d_to, user_id, keyword or "")
        if self.session.person is None:
            raise AppError("Please log in first.")
        return self.session.person.visible_records(rows)

    def export_csv(self, path, rows):
        write_csv(path, ["Date", "Product", "Specification", "SKU", "Type", "Quantity", "Unit Price", "User", "Remarks"],
                  [[str(r["transaction_date"]), r["product_name"], r["specification"] or "Not specified", r["sku"],
                    "Stock In" if r["transaction_type"] == "IN" else "Stock Out",
                    r["quantity"], r["unit_price"], r["username"], r["remarks"] or ""] for r in rows])


# ====================================================================== 5.0 Reports
class ReportController(BaseController):
    def __init__(self):
        super().__init__()
        self.transactions = TransactionRepository()

    def generate(self, date_from, date_to) -> dict:
        self.require("report.view", "generate reports")
        d_from, d_to = self.date_range(date_from, date_to, required=True)
        rows = []
        for r in self.transactions.report_rows(d_from, d_to):
            r["total_in"], r["total_out"] = int(r["total_in"]), int(r["total_out"])
            r["status"] = stock_status(r["stock_quantity"], r["low_stock_threshold"])
            rows.append(r)
        return {"rows": rows, "from": d_from, "to": d_to,
                "products": len(rows),
                "units_in_stock": sum(r["stock_quantity"] for r in rows),
                "stock_value": sum(r["stock_quantity"] * r["price"] for r in rows),
                "units_in": sum(r["total_in"] for r in rows),
                "units_sold": sum(r["total_out"] for r in rows),
                "low_items": sum(1 for r in rows if r["status"] != "OK")}

    def export_csv(self, path, report: dict):
        write_csv(path, ["Product", "Specification", "SKU", "Category", "Price", "Total Stock", "Stock In (period)",
                         "Total Sold (period)", "Status"],
                  [[r["product_name"], r["specification"] or "Not specified", r["sku"], r["category_name"], r["price"], r["stock_quantity"],
                    r["total_in"], r["total_out"], r["status"]] for r in report["rows"]])


# ====================================================================== 2.0 Users & roles
class DatabaseBackupController(BaseController):
    def __init__(self):
        super().__init__()
        self.backups = DatabaseBackup()

    def create_backup(self, path):
        self.require("user.manage", "back up the database")
        self.backups.create(path)

    def restore_backup(self, path):
        self.require("user.manage", "restore the database")
        self.backups.restore(path)


class UserManagementController(BaseController):
    def __init__(self):
        super().__init__()
        self.users, self.roles = UserRepository(), RoleRepository()

    def list_users(self):
        self.require("user.manage", "manage users")
        return self.users.find_all_with_roles()

    def list_roles(self):
        self.require("user.manage", "manage users")
        return self.roles.find_all()

    def create_user(self, username, password, confirm, role_id, full_name, email="", contact=""):
        self.require("user.manage", "create users")
        username, full_name = (username or "").strip(), (full_name or "").strip()
        email, contact = (email or "").strip(), (contact or "").strip()
        if not Validator.is_valid_username(username):
            raise AppError(USERNAME_HINT)
        if not full_name:
            raise AppError("Full name is required.")
        if email and not Validator.is_valid_email(email):
            raise AppError("That email address does not look right.")
        if len(full_name) > 150 or len(email) > 150 or len(contact) > 20:
            raise AppError("One of the fields is too long.")
        if not role_id:
            raise AppError("Please choose a role.")
        self.check_password(password, confirm)
        if self.users.exists_by_username(username):
            raise AppError("That username is already taken.")
        if email and self.users.email_in_use(email):
            raise AppError("That email address is already used by another account.")
        role = self.roles.find_by_id(role_id)
        with self.db.transaction() as cur:
            uid = self.users.create(username, hash_password(password), role_id, full_name, email, contact, cur)
            self.audit.log("INSERT", "users", uid, None,
                           {"username": username, "role": role["role_name"], "full_name": full_name}, cursor=cur)

    def _target(self, user_id, cur=None):
        target = self.users.find_detail(user_id, cur)
        if target is None:
            raise AppError("That user no longer exists.")
        return target

    def _protect_last_admin(self, target):
        if target["role_name"] == "Admin" and target["is_active"] and self.users.count_active_admins() <= 1:
            raise AppError("This is the last active Admin. Create or promote another Admin first.")

    def change_role(self, user_id, role_id):
        self.require("user.manage", "change roles")
        if user_id == self.me["user_id"]:
            raise AppError("You cannot change your own role.")
        with self.db.transaction() as cur:
            target = self._target(user_id, cur)
            new_role = self.roles.find_by_id(role_id, cur)
            if new_role["role_name"] != "Admin":
                self._protect_last_admin(target)
            self.users.update_role(user_id, role_id, cur)
            self.audit.log("UPDATE", "users", user_id, {"role": target["role_name"]},
                           {"role": new_role["role_name"]}, cursor=cur)

    def set_active(self, user_id, active: bool):
        self.require("user.manage", "activate or deactivate users")
        if user_id == self.me["user_id"]:
            raise AppError("You cannot deactivate your own account.")
        with self.db.transaction() as cur:
            target = self._target(user_id, cur)
            if not active:
                self._protect_last_admin(target)
            self.users.set_active(user_id, active, cur)
            self.audit.log("UPDATE", "users", user_id, {"is_active": target["is_active"]},
                           {"is_active": int(active)}, cursor=cur)

    def reset_password(self, user_id, new_password, confirm):
        self.require("user.manage", "reset passwords")
        self.check_password(new_password, confirm)
        with self.db.transaction() as cur:
            self._target(user_id, cur)
            self.users.set_password(user_id, hash_password(new_password), cur)
            self.audit.log("UPDATE", "users", user_id, None, {"password": "reset by admin"}, cursor=cur)

    # ---- role <-> permission assignment ----
    def permission_matrix(self, role_id):
        self.require("user.manage", "manage permissions")
        return self.roles.all_permissions(), self.roles.granted_permission_ids(role_id)

    def save_role_permissions(self, role_id, permission_ids):
        self.require("user.manage", "manage permissions")
        role = self.roles.find_by_id(role_id)
        ids = set(permission_ids)
        if role["role_name"] == "Admin":      # an Admin can never lock every Admin out
            ids |= {p["permission_id"] for p in self.roles.all_permissions()
                    if p["permission_name"] in ("user.manage", "audit.view", "dashboard.view")}
        with self.db.transaction() as cur:
            before = self.roles.find_permissions(role_id)
            self.roles.assign_permissions(role_id, sorted(ids), cur)
            after = {p["permission_name"] for p in self.roles.all_permissions() if p["permission_id"] in ids}
            self.audit.log("UPDATE", "role_permissions", role_id,
                           {"role": role["role_name"], "permissions": sorted(before)},
                           {"role": role["role_name"], "permissions": sorted(after)}, cursor=cur)
        if role["role_name"] == self.me["role"]:
            self.session.permissions = self.roles.find_permissions(role_id)


# ====================================================================== 7.0 Audit trail
class AuditLogController(BaseController):
    def __init__(self):
        super().__init__()
        self.logs, self.users = AuditLogRepository(), UserRepository()

    def list_users(self):
        self.require("audit.view", "view the audit trail")
        return self.users.find_all_with_roles()

    def list_logs(self, user_id=None, action=None, date_from="", date_to=""):
        self.require("audit.view", "view the audit trail")
        d_from, d_to = self.date_range(date_from, date_to)
        return self.logs.find_by_filter(user_id, action, d_from, d_to)
