"""Unit tests that need neither MySQL nor a display:  python -m unittest discover -s tests"""
import sys
import types
import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:                                              # use a tiny stub when the driver isn't installed
    import mysql.connector  # noqa: F401
except ModuleNotFoundError:
    mysql = types.ModuleType("mysql")
    connector = types.ModuleType("mysql.connector")
    connector.Error = type("Error", (Exception,), {})
    connector.IntegrityError = type("IntegrityError", (connector.Error,), {})
    connector.errorcode = types.SimpleNamespace(ER_ACCESS_DENIED_ERROR=1045, CR_CONN_HOST_ERROR=2003)
    mysql.connector = connector
    errors_mod = types.ModuleType("mysql.connector.errorcode")
    errors_mod.ER_ACCESS_DENIED_ERROR, errors_mod.CR_CONN_HOST_ERROR = 1045, 2003
    sys.modules.update({"mysql": mysql, "mysql.connector": connector, "mysql.connector.errorcode": errors_mod})
    connector.errorcode = errors_mod

from app import services                              # noqa: E402
from app.errors import AuthError, PermissionDenied, ValidationError  # noqa: E402
from app.security import hash_password, verify_password  # noqa: E402
from app.session import CurrentUser, Session           # noqa: E402
from app.validators import parse_date, parse_int, parse_price  # noqa: E402


class Store:
    """In-memory stand-in for the repositories."""
    def __init__(self):
        self.users, self.products, self.tx, self.cats, self.audit_rows = {}, {}, [], {}, []
        self.next = {"p": 1, "t": 1, "c": 1, "u": 1}


STORE = Store()


class FakeDB:
    @contextmanager
    def transaction(self):
        snapshot = ({k: dict(v) for k, v in STORE.products.items()}, list(STORE.tx))
        try:
            yield None
        except BaseException:
            STORE.products, STORE.tx = snapshot
            raise


class FakeUsers:
    def get_by_username(self, name):
        return STORE.users.get(name)
    def create(self, username, pw, role_id, cur=None):
        uid = STORE.next["u"]; STORE.next["u"] += 1
        STORE.users[username] = dict(user_id=uid, username=username, password=pw, role_id=role_id,
                                     is_active=1, role_name="Staff")
        return uid
    def permissions_for_role(self, role_id):
        return frozenset({"product.view", "product.add", "product.edit", "stock.add", "stock.remove",
                          "transaction.view", "report.view"})


class FakeRoles:
    def get_id(self, name): return 2


class FakeAudit:
    def log(self, *a, **k): STORE.audit_rows.append((a, k))


class FakeCats:
    def all(self): return list(STORE.cats.values())
    def find_by_name(self, name, cur=None):
        return next((c for c in STORE.cats.values() if c["category_name"] == name), None)
    def create(self, name, cur=None):
        cid = STORE.next["c"]; STORE.next["c"] += 1
        STORE.cats[cid] = {"category_id": cid, "category_name": name}
        return cid


class FakeProducts:
    def find_by_name(self, name, cur=None):
        return next((p for p in STORE.products.values() if p["product_name"] == name), None)
    def create(self, name, cat, price, stock, thr, cur=None):
        pid = STORE.next["p"]; STORE.next["p"] += 1
        STORE.products[pid] = dict(product_id=pid, product_name=name, category_id=cat, price=price,
                                   stock_quantity=stock, low_stock_threshold=thr, is_active=1,
                                   category_name=None)
        return pid
    def revive(self, pid, name, cat, price, stock, thr, cur=None):
        STORE.products[pid].update(product_name=name, category_id=cat, price=price,
                                   stock_quantity=stock, low_stock_threshold=thr, is_active=1)
    def get(self, pid, cur=None): return STORE.products.get(pid)
    def get_active_for_update(self, pid, cur):
        p = STORE.products.get(pid)
        return p if p and p["is_active"] else None
    def set_stock(self, pid, q, cur=None): STORE.products[pid]["stock_quantity"] = q
    def deactivate(self, pid, cur=None): STORE.products[pid]["is_active"] = 0
    def update(self, pid, name, cat, price, thr, cur=None):
        STORE.products[pid].update(product_name=name, category_id=cat, price=price, low_stock_threshold=thr)


class FakeTx:
    def insert(self, pid, uid, kind, qty, remarks, cur=None):
        STORE.tx.append((pid, uid, kind, qty, remarks)); return len(STORE.tx)
    def report(self, start, end): return []


def install_fakes():
    services.Database = FakeDB
    services.UserRepository, services.RoleRepository, services.AuditRepository = FakeUsers, FakeRoles, FakeAudit
    services.CategoryRepository, services.ProductRepository, services.TransactionRepository = FakeCats, FakeProducts, FakeTx


class ValidatorTests(unittest.TestCase):
    def test_price(self):
        self.assertEqual(parse_price("\u20b11,045.5"), Decimal("1045.50"))
        for bad in ("", "abc", "-5", "0", "nan", "99999999"):
            with self.assertRaises(ValidationError):
                parse_price(bad)

    def test_int(self):
        self.assertEqual(parse_int(" 12 ", "Qty"), 12)
        for bad in ("", "1.5", "-3", "0", "abc", "9999999"):
            with self.assertRaises(ValidationError):
                parse_int(bad, "Qty")

    def test_date(self):
        self.assertEqual(parse_date("2025-09-01", "D"), date(2025, 9, 1))
        for bad in ("", "01/09/2025", "2025-13-01", "2025-02-30"):
            with self.assertRaises(ValidationError):
                parse_date(bad, "D")

    def test_password_hash(self):
        h = hash_password("secret1")
        self.assertTrue(verify_password("secret1", h))
        self.assertFalse(verify_password("secret2", h))
        self.assertNotEqual(h, hash_password("secret1"))      # salted
        self.assertFalse(verify_password("x", "garbage"))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        global STORE
        STORE = Store()
        install_fakes()
        Session.end()

    def login(self):
        auth = services.AuthService()
        auth.register("marvin", "secret1", "secret1")
        return auth.login("marvin", "secret1")

    def test_register_rules(self):
        auth = services.AuthService()
        for args in [("", "secret1", "secret1"), ("ab", "secret1", "secret1"), ("bad name", "secret1", "secret1"),
                     ("marvin", "123", "123"), ("marvin", "secret1", "secret2")]:
            with self.assertRaises(ValidationError):
                auth.register(*args)
        auth.register("marvin", "secret1", "secret1")
        with self.assertRaises(ValidationError):
            auth.register("marvin", "secret1", "secret1")

    def test_login(self):
        auth = services.AuthService()
        auth.register("marvin", "secret1", "secret1")
        for u, p in [("marvin", "wrong"), ("nobody", "secret1")]:
            with self.assertRaises(AuthError):
                auth.login(u, p)
        self.assertIsNone(Session.current())
        self.assertEqual(auth.login("marvin", "secret1").username, "marvin")
        auth.logout()
        self.assertIsNone(Session.current())

    def test_permissions_enforced(self):
        with self.assertRaises(PermissionDenied):
            services.InventoryService().add_product("Rice", "", "45", "5", "10")
        self.login()
        with self.assertRaises(PermissionDenied):                # staff cannot delete
            services.InventoryService().delete_product(1)

    def test_product_and_stock_flow(self):
        self.login()
        inv = services.InventoryService()
        pid = inv.add_product("Rice (1kg)", "Groceries", "45", "10", "")
        self.assertEqual(STORE.products[pid]["stock_quantity"], 10)
        self.assertEqual(STORE.products[pid]["low_stock_threshold"], 10)
        self.assertEqual(len(STORE.tx), 1)                       # initial stock recorded
        with self.assertRaises(ValidationError):                 # duplicate name
            inv.add_product("Rice (1kg)", "", "45", "1", "10")
        res = inv.adjust_stock(pid, "3", services.STOCK_OUT, "sold")
        self.assertEqual(res["stock"], 7)
        self.assertTrue(res["low"])
        with self.assertRaises(ValidationError):                 # cannot go negative
            inv.adjust_stock(pid, "8", services.STOCK_OUT)
        self.assertEqual(STORE.products[pid]["stock_quantity"], 7)
        self.assertEqual(inv.adjust_stock(pid, "5", services.STOCK_IN)["stock"], 12)
        for bad in ("0", "-1", "x", ""):
            with self.assertRaises(ValidationError):
                inv.adjust_stock(pid, bad, services.STOCK_IN)

    def test_report_date_rules(self):
        self.login()
        rep = services.ReportService()
        for a, b in [("", "2025-09-30"), ("2025-09-30", "2025-09-01"), ("2025-09-01", "oops")]:
            with self.assertRaises(ValidationError):
                rep.inventory_report(a, b)
        self.assertEqual(rep.inventory_report("2025-09-01", "2025-09-30"), [])


if __name__ == "__main__":
    unittest.main()
