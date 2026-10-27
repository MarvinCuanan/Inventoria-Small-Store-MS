"""Repository / DAO layer: every SQL statement in the app lives here (all parameterised)."""
import json
import socket

from .database import Database


class BaseRepository:
    def __init__(self):
        self.db = Database()

    def _all(self, sql, params=(), cur=None):
        if cur is None:
            return self.db.query(sql, params)
        cur.execute(sql, params)
        return cur.fetchall()

    def _one(self, sql, params=(), cur=None):
        if cur is None:
            return self.db.query(sql, params, one=True)
        cur.execute(sql, params)
        return cur.fetchone()

    def _exec(self, sql, params=(), cur=None):
        if cur is None:
            return self.db.execute(sql, params)
        cur.execute(sql, params)
        return cur.lastrowid


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class RoleRepository(BaseRepository):
    def get_id(self, role_name):
        row = self._one("SELECT role_id FROM roles WHERE role_name=%s", (role_name,))
        return row["role_id"] if row else None


class UserRepository(BaseRepository):
    def get_by_username(self, username):
        return self._one(
            """SELECT u.user_id, u.username, u.password, u.role_id, u.is_active, r.role_name
               FROM users u LEFT JOIN roles r ON r.role_id = u.role_id
               WHERE u.username = %s""", (username,))

    def create(self, username, password_hash, role_id, cur=None):
        return self._exec(
            "INSERT INTO users (username, password, role_id) VALUES (%s, %s, %s)",
            (username, password_hash, role_id), cur)

    def count_by_role(self, role_id):
        return self._one("SELECT COUNT(*) AS n FROM users WHERE role_id=%s", (role_id,))["n"]

    def permissions_for_role(self, role_id):
        rows = self._all(
            """SELECT p.permission_name FROM role_permissions rp
               JOIN permissions p ON p.permission_id = rp.permission_id
               WHERE rp.role_id = %s""", (role_id,))
        return frozenset(r["permission_name"] for r in rows)


class CategoryRepository(BaseRepository):
    def all(self):
        return self._all("SELECT category_id, category_name FROM categories ORDER BY category_name")

    def find_by_name(self, name, cur=None):
        return self._one("SELECT category_id, category_name FROM categories WHERE category_name=%s",
                         (name,), cur)

    def create(self, name, cur=None):
        return self._exec("INSERT INTO categories (category_name) VALUES (%s)", (name,), cur)


class ProductRepository(BaseRepository):
    _SELECT = """SELECT p.product_id, p.product_name, p.category_id, c.category_name, p.price,
                        p.stock_quantity, p.low_stock_threshold, p.is_active
                 FROM products p LEFT JOIN categories c ON c.category_id = p.category_id"""

    def list_active(self, search=None):
        sql = self._SELECT + " WHERE p.is_active = 1"
        params = []
        if search:
            sql += " AND (p.product_name LIKE %s OR c.category_name LIKE %s)"
            params += [_like(search), _like(search)]
        return self._all(sql + " ORDER BY p.product_id", params)

    def get(self, product_id, cur=None):
        return self._one(self._SELECT + " WHERE p.product_id = %s", (product_id,), cur)

    def get_active_for_update(self, product_id, cur):
        return self._one(
            "SELECT product_id, product_name, stock_quantity, low_stock_threshold "
            "FROM products WHERE product_id=%s AND is_active=1 FOR UPDATE", (product_id,), cur)

    def find_by_name(self, name, cur=None):
        """Finds active *and* deleted products, because product names are UNIQUE."""
        return self._one(self._SELECT + " WHERE p.product_name = %s", (name,), cur)

    def find_active_by_name(self, name):
        return self._one(self._SELECT + " WHERE p.product_name = %s AND p.is_active = 1", (name,))

    def create(self, name, category_id, price, stock, threshold, cur=None):
        return self._exec(
            """INSERT INTO products (product_name, category_id, price, stock_quantity, low_stock_threshold)
               VALUES (%s, %s, %s, %s, %s)""", (name, category_id, price, stock, threshold), cur)

    def revive(self, product_id, name, category_id, price, stock, threshold, cur=None):
        """Re-activates a previously deleted product that has the same name."""
        self._exec(
            """UPDATE products SET product_name=%s, category_id=%s, price=%s, stock_quantity=%s,
                      low_stock_threshold=%s, is_active=1 WHERE product_id=%s""",
            (name, category_id, price, stock, threshold, product_id), cur)

    def update(self, product_id, name, category_id, price, threshold, cur=None):
        self._exec(
            """UPDATE products SET product_name=%s, category_id=%s, price=%s, low_stock_threshold=%s
               WHERE product_id=%s""", (name, category_id, price, threshold, product_id), cur)

    def deactivate(self, product_id, cur=None):
        self._exec("UPDATE products SET is_active=0 WHERE product_id=%s", (product_id,), cur)

    def set_stock(self, product_id, quantity, cur=None):
        self._exec("UPDATE products SET stock_quantity=%s WHERE product_id=%s", (quantity, product_id), cur)

    def stats(self):
        row = self._one(
            """SELECT COUNT(*) AS total_products,
                      COALESCE(SUM(stock_quantity), 0) AS total_stock,
                      COALESCE(SUM(stock_quantity <= low_stock_threshold), 0) AS low_stock
               FROM products WHERE is_active = 1""")
        return {k: int(v) for k, v in row.items()}

    def low_stock(self, limit=100):
        return self._all(
            """SELECT product_id, product_name, stock_quantity, low_stock_threshold
               FROM products WHERE is_active = 1 AND stock_quantity <= low_stock_threshold
               ORDER BY stock_quantity, product_name LIMIT %s""", (limit,))


class TransactionRepository(BaseRepository):
    def insert(self, product_id, user_id, kind, quantity, remarks, cur=None):
        return self._exec(
            """INSERT INTO transactions (product_id, user_id, transaction_type, quantity, remarks)
               VALUES (%s, %s, %s, %s, %s)""", (product_id, user_id, kind, quantity, remarks or None), cur)

    def search(self, kind=None, day=None, limit=500):
        sql = """SELECT t.transaction_id, t.transaction_date, p.product_name, t.transaction_type,
                        t.quantity, u.username, t.remarks
                 FROM transactions t
                 JOIN products p ON p.product_id = t.product_id
                 JOIN users u ON u.user_id = t.user_id WHERE 1=1"""
        params = []
        if kind:
            sql += " AND t.transaction_type = %s"
            params.append(kind)
        if day:
            sql += " AND DATE(t.transaction_date) = %s"
            params.append(day)
        sql += " ORDER BY t.transaction_date DESC, t.transaction_id DESC LIMIT %s"
        params.append(limit)
        return self._all(sql, params)

    def count_today(self):
        return int(self._one(
            "SELECT COUNT(*) AS n FROM transactions WHERE DATE(transaction_date) = CURDATE()")["n"])

    def report(self, start, end_exclusive):
        return self._all(
            """SELECT p.product_id, p.product_name, p.stock_quantity AS total_stock,
                      COALESCE(SUM(CASE WHEN t.transaction_type = 'Stock Out' THEN t.quantity END), 0) AS total_sold,
                      COALESCE(SUM(CASE WHEN t.transaction_type = 'Stock In'  THEN t.quantity END), 0) AS total_received
               FROM products p
               LEFT JOIN transactions t ON t.product_id = p.product_id
                    AND t.transaction_date >= %s AND t.transaction_date < %s
               WHERE p.is_active = 1
               GROUP BY p.product_id, p.product_name, p.stock_quantity
               ORDER BY p.product_name""", (start, end_exclusive))


class AuditRepository(BaseRepository):
    _ip_cache = None

    @classmethod
    def _ip(cls):
        if cls._ip_cache is None:
            try:
                cls._ip_cache = socket.gethostbyname(socket.gethostname())
            except OSError:
                cls._ip_cache = "127.0.0.1"
        return cls._ip_cache

    def log(self, user_id, action, table, record_id=None, old=None, new=None, cur=None):
        dump = lambda v: None if v is None else json.dumps(v, default=str, ensure_ascii=False)
        self._exec(
            """INSERT INTO audit_logs (user_id, action, table_affected, record_id, old_values, new_values, ip_address)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, action, table, record_id, dump(old), dump(new), self._ip()), cur)
