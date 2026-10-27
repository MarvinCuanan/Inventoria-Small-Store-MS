"""Data Access Layer - every SQL statement lives here (Repository / DAO pattern).

All methods take an optional `cursor`; pass the one from `db.transaction()` to make several
changes succeed or fail together.
"""
from __future__ import annotations

from core.database import DatabaseManager


def _like(keyword: str) -> str:
    k = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{k}%"


class BaseRepository:
    table = ""
    pk = "id"

    def __init__(self):
        self.db = DatabaseManager.get_instance()

    def find_by_id(self, record_id, cursor=None, for_update=False):
        sql = f"SELECT * FROM {self.table} WHERE {self.pk}=%s" + (" FOR UPDATE" if for_update else "")
        rows = self.db.query(sql, (record_id,), cursor)
        return rows[0] if rows else None

    def find_all(self):
        return self.db.query(f"SELECT * FROM {self.table} ORDER BY {self.pk}")


# ---------------------------------------------------------------- roles
class RoleRepository(BaseRepository):
    table, pk = "roles", "role_id"

    def find_by_name(self, name):
        rows = self.db.query("SELECT * FROM roles WHERE role_name=%s", (name,))
        return rows[0] if rows else None

    def find_permissions(self, role_id) -> set[str]:
        rows = self.db.query(
            "SELECT p.permission_name FROM role_permissions rp "
            "JOIN permissions p ON p.permission_id = rp.permission_id WHERE rp.role_id=%s", (role_id,))
        return {r["permission_name"] for r in rows}

    def all_permissions(self):
        return self.db.query("SELECT * FROM permissions ORDER BY permission_id")

    def granted_permission_ids(self, role_id) -> set[int]:
        rows = self.db.query("SELECT permission_id FROM role_permissions WHERE role_id=%s", (role_id,))
        return {r["permission_id"] for r in rows}

    def assign_permissions(self, role_id, permission_ids, cursor):
        self.db.execute("DELETE FROM role_permissions WHERE role_id=%s", (role_id,), cursor)
        for pid in permission_ids:
            self.db.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (%s,%s)",
                            (role_id, pid), cursor)


# ---------------------------------------------------------------- users
class UserRepository(BaseRepository):
    table, pk = "users", "user_id"
    _SELECT = (
        "SELECT u.user_id, u.username, u.password_hash, u.is_active, u.last_login_at, u.created_at, "
        "u.role_id, r.role_name, p.full_name, p.email, p.contact_no "
        "FROM users u JOIN roles r ON r.role_id = u.role_id "
        "LEFT JOIN user_profiles p ON p.user_id = u.user_id ")

    def find_by_username(self, username):
        rows = self.db.query(self._SELECT + "WHERE u.username=%s", (username,))
        return rows[0] if rows else None

    def find_detail(self, user_id, cursor=None):
        rows = self.db.query(self._SELECT + "WHERE u.user_id=%s", (user_id,), cursor)
        return rows[0] if rows else None

    def find_all_with_roles(self):
        return self.db.query(self._SELECT + "ORDER BY u.username")

    def exists_by_username(self, username, cursor=None) -> bool:
        rows = self.db.query("SELECT 1 AS x FROM users WHERE username=%s", (username,), cursor)
        return bool(rows)

    def email_in_use(self, email, cursor=None) -> bool:
        rows = self.db.query("SELECT 1 AS x FROM user_profiles WHERE email=%s", (email,), cursor)
        return bool(rows)

    def create(self, username, password_hash, role_id, full_name, email=None, contact_no=None, cursor=None):
        if cursor is None:
            with self.db.transaction() as cur:
                return self.create(username, password_hash, role_id, full_name, email, contact_no, cur)
        _, user_id = self.db.execute(
            "INSERT INTO users (role_id, username, password_hash) VALUES (%s,%s,%s)",
            (role_id, username, password_hash), cursor)
        self.db.execute(
            "INSERT INTO user_profiles (user_id, full_name, email, contact_no) VALUES (%s,%s,%s,%s)",
            (user_id, full_name, email or None, contact_no or None), cursor)
        return user_id

    def update_role(self, user_id, role_id, cursor=None):
        self.db.execute("UPDATE users SET role_id=%s WHERE user_id=%s", (role_id, user_id), cursor)

    def set_active(self, user_id, active, cursor=None):
        self.db.execute("UPDATE users SET is_active=%s WHERE user_id=%s", (1 if active else 0, user_id), cursor)

    def set_password(self, user_id, password_hash, cursor=None):
        self.db.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (password_hash, user_id), cursor)

    def touch_login(self, user_id):
        self.db.execute("UPDATE users SET last_login_at=NOW() WHERE user_id=%s", (user_id,))

    def count_active_admins(self) -> int:
        rows = self.db.query(
            "SELECT COUNT(*) AS n FROM users u JOIN roles r ON r.role_id=u.role_id "
            "WHERE r.role_name='Admin' AND u.is_active=1")
        return int(rows[0]["n"])

    def count_by_role(self, role_id) -> int:
        rows = self.db.query("SELECT COUNT(*) AS n FROM users WHERE role_id=%s", (role_id,))
        return int(rows[0]["n"])


# ---------------------------------------------------------------- categories
class CategoryRepository(BaseRepository):
    table, pk = "categories", "category_id"

    def find_all_with_counts(self):
        return self.db.query(
            "SELECT c.category_id, c.category_name, c.description, COUNT(p.product_id) AS product_count "
            "FROM categories c LEFT JOIN products p ON p.category_id = c.category_id "
            "GROUP BY c.category_id, c.category_name, c.description ORDER BY c.category_name")

    def exists_by_name(self, name, exclude_id=None) -> bool:
        rows = self.db.query("SELECT category_id FROM categories WHERE category_name=%s", (name,))
        return any(r["category_id"] != exclude_id for r in rows)

    def create(self, name, description, cursor=None):
        _, new_id = self.db.execute("INSERT INTO categories (category_name, description) VALUES (%s,%s)",
                                    (name, description or None), cursor)
        return new_id

    def update(self, category_id, name, description, cursor=None):
        self.db.execute("UPDATE categories SET category_name=%s, description=%s WHERE category_id=%s",
                        (name, description or None, category_id), cursor)

    def delete(self, category_id, cursor=None):
        self.db.execute("DELETE FROM categories WHERE category_id=%s", (category_id,), cursor)


# ---------------------------------------------------------------- products
class ProductRepository(BaseRepository):
    table, pk = "products", "product_id"
    _SELECT = ("SELECT p.*, c.category_name FROM products p "
               "JOIN categories c ON c.category_id = p.category_id ")

    def search(self, keyword="", include_inactive=False):
        sql, params, where = self._SELECT, [], []
        if keyword.strip():
            like = _like(keyword.strip())
            where.append("(p.product_name LIKE %s OR p.specification LIKE %s OR "
                         "p.sku LIKE %s OR c.category_name LIKE %s)")
            params += [like, like, like, like]
        if not include_inactive:
            where.append("p.is_active = 1")
        if where:
            sql += "WHERE " + " AND ".join(where) + " "
        return self.db.query(sql + "ORDER BY p.product_name", params)

    def find_active(self):
        return self.search("", False)

    def exists_by_name(self, name, specification, exclude_id=None) -> bool:
        rows = self.db.query(
            "SELECT product_id FROM products WHERE product_name=%s AND specification=%s",
            (name, specification))
        return any(r["product_id"] != exclude_id for r in rows)

    def exists_sku(self, sku, exclude_id=None) -> bool:
        rows = self.db.query("SELECT product_id FROM products WHERE sku=%s", (sku,))
        return any(r["product_id"] != exclude_id for r in rows)

    def create(self, sku, name, specification, category_id, price, stock, threshold, cursor=None):
        _, new_id = self.db.execute(
            "INSERT INTO products (sku, product_name, specification, category_id, price, stock_quantity, "
            "low_stock_threshold) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (sku, name, specification, category_id, price, stock, threshold), cursor)
        return new_id

    def update(self, product_id, sku, name, specification, category_id, price, threshold, is_active, cursor=None):
        self.db.execute(
            "UPDATE products SET sku=%s, product_name=%s, specification=%s, category_id=%s, price=%s, "
            "low_stock_threshold=%s, is_active=%s WHERE product_id=%s",
            (sku, name, specification, category_id, price, threshold, 1 if is_active else 0, product_id), cursor)

    def set_sku(self, product_id, sku, cursor=None):
        self.db.execute("UPDATE products SET sku=%s WHERE product_id=%s", (sku, product_id), cursor)

    def set_active(self, product_id, active, cursor=None):
        self.db.execute("UPDATE products SET is_active=%s WHERE product_id=%s",
                        (1 if active else 0, product_id), cursor)

    def update_stock(self, product_id, new_quantity, cursor=None):
        self.db.execute("UPDATE products SET stock_quantity=%s WHERE product_id=%s",
                        (new_quantity, product_id), cursor)

    def count_active(self) -> int:
        return int(self.db.query("SELECT COUNT(*) AS n FROM products WHERE is_active=1")[0]["n"])

    def sum_stock(self) -> int:
        return int(self.db.query(
            "SELECT COALESCE(SUM(stock_quantity),0) AS n FROM products WHERE is_active=1")[0]["n"])

    def find_low_stock(self):
        return self.db.query(
            self._SELECT + "WHERE p.is_active=1 AND p.stock_quantity <= p.low_stock_threshold "
                           "ORDER BY p.stock_quantity, p.product_name")


# ---------------------------------------------------------------- transactions
class TransactionRepository(BaseRepository):
    table, pk = "transactions", "transaction_id"

    def create(self, product_id, user_id, unit_price, tx_type, quantity, remarks=None, cursor=None):
        _, new_id = self.db.execute(
            "INSERT INTO transactions (product_id, user_id, unit_price, transaction_type, quantity, remarks) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (product_id, user_id, unit_price, tx_type, quantity, remarks or None), cursor)
        return new_id

    def find_by_filter(self, tx_type=None, date_from=None, date_to=None, user_id=None, keyword="", limit=2000):
        sql = ("SELECT t.transaction_id, t.user_id, t.transaction_date, p.product_name, p.specification, p.sku, t.transaction_type, "
               "t.quantity, t.unit_price, u.username, t.remarks "
               "FROM transactions t JOIN products p ON p.product_id = t.product_id "
               "JOIN users u ON u.user_id = t.user_id WHERE 1=1 ")
        params = []
        if tx_type:
            sql += "AND t.transaction_type=%s "
            params.append(tx_type)
        if date_from:
            sql += "AND t.transaction_date >= %s "
            params.append(date_from)
        if date_to:
            sql += "AND t.transaction_date < DATE_ADD(%s, INTERVAL 1 DAY) "
            params.append(date_to)
        if user_id:
            sql += "AND t.user_id=%s "
            params.append(user_id)
        if keyword.strip():
            sql += "AND (p.product_name LIKE %s OR p.specification LIKE %s OR p.sku LIKE %s) "
            like = _like(keyword.strip())
            params += [like, like, like]
        sql += "ORDER BY t.transaction_date DESC, t.transaction_id DESC LIMIT %s"
        params.append(limit)
        return self.db.query(sql, params)

    def count_by_date(self, day_iso) -> int:
        return int(self.db.query(
            "SELECT COUNT(*) AS n FROM transactions WHERE DATE(transaction_date)=%s", (day_iso,))[0]["n"])

    def report_rows(self, date_from, date_to):
        return self.db.query(
            "SELECT p.product_id, p.product_name, p.specification, p.sku, c.category_name, p.price, p.stock_quantity, "
            "p.low_stock_threshold, "
            "COALESCE(SUM(CASE WHEN t.transaction_type='IN'  THEN t.quantity END),0) AS total_in, "
            "COALESCE(SUM(CASE WHEN t.transaction_type='OUT' THEN t.quantity END),0) AS total_out "
            "FROM products p JOIN categories c ON c.category_id = p.category_id "
            "LEFT JOIN transactions t ON t.product_id = p.product_id "
            "  AND t.transaction_date >= %s AND t.transaction_date < DATE_ADD(%s, INTERVAL 1 DAY) "
            "WHERE p.is_active=1 "
            "GROUP BY p.product_id, p.product_name, p.specification, p.sku, c.category_name, p.price, "
            "p.stock_quantity, p.low_stock_threshold ORDER BY p.product_name",
            (date_from, date_to))


# ---------------------------------------------------------------- audit logs
class AuditLogRepository(BaseRepository):
    table, pk = "audit_logs", "log_id"

    def create(self, user_id, action, table, record_id, old_json, new_json, ip, cursor=None):
        self.db.execute(
            "INSERT INTO audit_logs (user_id, action, table_affected, record_id, old_values, new_values, ip_address) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)", (user_id, action, table, record_id, old_json, new_json, ip), cursor)

    def find_by_filter(self, user_id=None, action=None, date_from=None, date_to=None, limit=1000):
        sql = ("SELECT l.log_id, l.created_at, COALESCE(u.username,'(deleted user)') AS username, l.action, "
               "l.table_affected, l.record_id, l.old_values, l.new_values, l.ip_address "
               "FROM audit_logs l LEFT JOIN users u ON u.user_id = l.user_id WHERE 1=1 ")
        params = []
        if user_id:
            sql += "AND l.user_id=%s "
            params.append(user_id)
        if action:
            sql += "AND l.action=%s "
            params.append(action)
        if date_from:
            sql += "AND l.created_at >= %s "
            params.append(date_from)
        if date_to:
            sql += "AND l.created_at < DATE_ADD(%s, INTERVAL 1 DAY) "
            params.append(date_to)
        sql += "ORDER BY l.created_at DESC, l.log_id DESC LIMIT %s"
        params.append(limit)
        rows = self.db.query(sql, params)
        for row in rows:                      # some connector versions return JSON columns as bytes
            for key in ("old_values", "new_values"):
                if isinstance(row[key], (bytes, bytearray)):
                    row[key] = row[key].decode("utf-8", "replace")
        return rows
