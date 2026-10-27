"""Business logic: validation, permissions, atomic stock changes and audit logging."""
from datetime import timedelta

from .config import DEFAULT_LOW_STOCK_THRESHOLD
from .database import Database
from .errors import AppError, AuthError, ValidationError
from .repositories import (AuditRepository, CategoryRepository, ProductRepository, RoleRepository,
                           TransactionRepository, UserRepository)
from .security import hash_password, verify_password
from .session import CurrentUser, Session
from .validators import USERNAME_RE, clean_name, parse_date, parse_int, parse_price

STOCK_IN = "Stock In"
STOCK_OUT = "Stock Out"

_dummy_hash = None


def _safe_audit(audit, *args, **kwargs):
    """Audit logging must never break the action that triggered it."""
    try:
        audit.log(*args, **kwargs)
    except AppError:
        pass


class AuthService:
    def __init__(self):
        self.users, self.roles, self.audit = UserRepository(), RoleRepository(), AuditRepository()

    def register(self, username, password, confirm):
        username = (username or "").strip()
        if not username or not password or not confirm:
            raise ValidationError("Please fill in all fields.")
        if not USERNAME_RE.match(username):
            raise ValidationError("Username must be 3-30 characters: letters, numbers, dots or underscores.")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters.")
        if password != confirm:
            raise ValidationError("Passwords do not match.")
        if self.users.get_by_username(username):
            raise ValidationError("That username is already taken. Please choose another one.")
        user_id = self.users.create(username, hash_password(password), self.roles.get_id("Staff"))
        _safe_audit(self.audit, user_id, "REGISTER", "users", user_id, new={"username": username})

    def login(self, username, password):
        global _dummy_hash
        username = (username or "").strip()
        if not username or not password:
            raise ValidationError("Please enter your username and password.")
        row = self.users.get_by_username(username)
        if row is None:                                   # keep timing similar for unknown users
            _dummy_hash = _dummy_hash or hash_password("not-a-real-password")
            verify_password(password, _dummy_hash)
        if row is None or not verify_password(password, row["password"]):
            _safe_audit(self.audit, row["user_id"] if row else None, "LOGIN_FAIL", "users",
                        row["user_id"] if row else None, new={"username": username})
            raise AuthError("Invalid username or password.")
        if not row["is_active"]:
            raise AuthError("This account is deactivated. Please contact the administrator.")
        user = CurrentUser(row["user_id"], row["username"], row["role_name"] or "Staff",
                           self.users.permissions_for_role(row["role_id"]))
        Session.start(user)
        _safe_audit(self.audit, user.user_id, "LOGIN", "users", user.user_id)
        return user

    def logout(self):
        user = Session.current()
        if user:
            _safe_audit(self.audit, user.user_id, "LOGOUT", "users", user.user_id)
        Session.end()


class InventoryService:
    def __init__(self):
        self.db = Database()
        self.products, self.categories = ProductRepository(), CategoryRepository()
        self.transactions, self.audit = TransactionRepository(), AuditRepository()

    # ---------- read ----------
    def list_products(self, search=""):
        Session.require("product.view")
        return self.products.list_active((search or "").strip() or None)

    def product_names(self):
        return self.products.list_active()

    def categories_list(self):
        return self.categories.all()

    def dashboard(self):
        stats = self.products.stats()
        stats["today_transactions"] = self.transactions.count_today()
        stats["low_stock_items"] = self.products.low_stock()
        return stats

    def search_transactions(self, kind="All", day_text=""):
        Session.require("transaction.view")
        kind = None if kind in ("", "All", None) else kind
        if kind not in (None, STOCK_IN, STOCK_OUT):
            raise ValidationError("Unknown transaction type.")
        day = parse_date(day_text, "Date") if (day_text or "").strip() else None
        return self.transactions.search(kind, day)

    # ---------- products ----------
    def _resolve_category(self, name, cur):
        name = " ".join((name or "").split())
        if not name or name.startswith("("):
            return None
        if len(name) > 100:
            raise ValidationError("Category must be 100 characters or fewer.")
        found = self.categories.find_by_name(name, cur)
        return found["category_id"] if found else self.categories.create(name, cur)

    def add_product(self, name, category, price, stock, threshold):
        user = Session.require("product.add")
        name = clean_name(name, "Product name", 150)
        price = parse_price(price)
        stock = parse_int(stock or "0", "Initial stock", minimum=0)
        threshold = parse_int(threshold or DEFAULT_LOW_STOCK_THRESHOLD, "Low-stock level", minimum=0)
        with self.db.transaction() as cur:
            category_id = self._resolve_category(category, cur)
            existing = self.products.find_by_name(name, cur)
            if existing and existing["is_active"]:
                raise ValidationError(f'A product named "{name}" already exists.')
            if existing:                                  # previously deleted: bring it back
                product_id = existing["product_id"]
                self.products.revive(product_id, name, category_id, price, stock, threshold, cur)
            else:
                product_id = self.products.create(name, category_id, price, stock, threshold, cur)
            if stock > 0:
                self.transactions.insert(product_id, user.user_id, STOCK_IN, stock, "Initial stock", cur)
            self.audit.log(user.user_id, "CREATE", "products", product_id,
                           new={"name": name, "price": price, "stock": stock}, cur=cur)
        return product_id

    def update_product(self, product_id, name, category, price, threshold):
        user = Session.require("product.edit")
        name = clean_name(name, "Product name", 150)
        price = parse_price(price)
        threshold = parse_int(threshold, "Low-stock level", minimum=0)
        with self.db.transaction() as cur:
            old = self.products.get(product_id, cur)
            if not old or not old["is_active"]:
                raise ValidationError("This product no longer exists.")
            clash = self.products.find_by_name(name, cur)
            if clash and clash["product_id"] != product_id:
                raise ValidationError(f'Another product named "{name}" already exists.')
            category_id = self._resolve_category(category, cur)
            self.products.update(product_id, name, category_id, price, threshold, cur)
            self.audit.log(user.user_id, "UPDATE", "products", product_id,
                           old={"name": old["product_name"], "price": old["price"],
                                "threshold": old["low_stock_threshold"]},
                           new={"name": name, "price": price, "threshold": threshold}, cur=cur)

    def delete_product(self, product_id):
        user = Session.require("product.delete")
        with self.db.transaction() as cur:
            old = self.products.get(product_id, cur)
            if not old or not old["is_active"]:
                raise ValidationError("This product no longer exists.")
            self.products.deactivate(product_id, cur)
            self.audit.log(user.user_id, "DELETE", "products", product_id,
                           old={"name": old["product_name"], "stock": old["stock_quantity"]}, cur=cur)

    # ---------- stock ----------
    def adjust_stock(self, product_id, quantity, kind, remarks=""):
        if kind not in (STOCK_IN, STOCK_OUT):
            raise ValidationError("Choose Add Stock or Remove Stock.")
        user = Session.require("stock.add" if kind == STOCK_IN else "stock.remove")
        if product_id is None:
            raise ValidationError("Please choose a product from the list.")
        qty = parse_int(quantity, "Quantity")
        remarks = (remarks or "").strip()
        if len(remarks) > 255:
            raise ValidationError("Remarks must be 255 characters or fewer.")
        with self.db.transaction() as cur:
            product = self.products.get_active_for_update(product_id, cur)   # row lock
            if not product:
                raise ValidationError("This product no longer exists.")
            old_stock = product["stock_quantity"]
            new_stock = old_stock + qty if kind == STOCK_IN else old_stock - qty
            if new_stock < 0:
                raise ValidationError(f"Not enough stock. Only {old_stock} available for "
                                      f'"{product["product_name"]}".')
            self.products.set_stock(product_id, new_stock, cur)
            tx_id = self.transactions.insert(product_id, user.user_id, kind, qty, remarks, cur)
            self.audit.log(user.user_id, "STOCK_IN" if kind == STOCK_IN else "STOCK_OUT",
                           "transactions", tx_id, old={"stock": old_stock}, new={"stock": new_stock}, cur=cur)
        return {"name": product["product_name"], "stock": new_stock,
                "threshold": product["low_stock_threshold"], "low": new_stock <= product["low_stock_threshold"]}


class ReportService:
    def __init__(self):
        self.transactions = TransactionRepository()

    def inventory_report(self, from_text, to_text):
        Session.require("report.view")
        if not (from_text or "").strip() or not (to_text or "").strip():
            raise ValidationError("Please select both a From date and a To date.")
        start = parse_date(from_text, "From date")
        end = parse_date(to_text, "To date")
        if start > end:
            raise ValidationError("The From date must not be later than the To date.")
        rows = self.transactions.report(start, end + timedelta(days=1))
        for row in rows:
            row["total_sold"] = int(row["total_sold"])
            row["total_received"] = int(row["total_received"])
        return rows
