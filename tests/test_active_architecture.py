"""Tests for domain and repository code used by main.py."""
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.bootstrap as bootstrap
from core.domain import Admin, PasswordCredentials, Person, Staff, StockLevel
from core.errors import DatabaseError, PermissionDenied, ValidationError
from core.database import DatabaseManager
from core.security import verify_password
from core.session import SessionManager
from repositories import (AuditLogRepository, CategoryRepository, ProductRepository, RoleRepository,
                          TransactionRepository, UserRepository)


class StubDatabase:
    def __init__(self):
        self.rows = []
        self.error = None
        self.calls = []

    def query(self, sql, params=None, cursor=None):
        self.calls.append(("query", sql, params, cursor))
        if self.error:
            raise self.error
        return self.rows

    def execute(self, sql, params=None, cursor=None):
        self.calls.append(("execute", sql, params, cursor))
        if self.error:
            raise self.error
        return 1, 23


class DomainTests(unittest.TestCase):
    def test_person_abstraction_and_polymorphic_visibility(self):
        with self.assertRaises(TypeError):
            Person(1, "admin")

        people = [Admin(1, "admin"), Staff(2, "staff")]
        records = [{"user_id": 1}, {"user_id": 2}]
        self.assertEqual([person.visible_records(records) for person in people],
                         [[{"user_id": 1}, {"user_id": 2}], [{"user_id": 2}]])

    def test_password_hash_is_read_only(self):
        credential = PasswordCredentials("pbkdf-hash")
        self.assertEqual(credential.password_hash, "pbkdf-hash")
        with self.assertRaises(AttributeError):
            credential.password_hash = "plaintext"

    def test_stock_level_validates_quantity(self):
        stock = StockLevel(8)
        self.assertEqual(stock.increase(2), 10)
        self.assertEqual(stock.decrease(3), 7)
        for invalid in (-1, 1.5, True):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                stock.quantity = invalid
        with self.assertRaises(ValidationError):
            stock.decrease(8)
        self.assertEqual(stock.quantity, 7)

    def test_session_keeps_hash_out_of_user_view_and_uses_role_subclass(self):
        session = SessionManager()
        session.start(
            {"user_id": 4, "username": "staff", "password_hash": "stored-hash", "role": "Staff"},
            {"transaction.view_own"},
        )
        self.assertNotIn("password_hash", session.current_user)
        self.assertIsInstance(session.person, Staff)
        self.assertEqual(session.person.visible_records([{"user_id": 4}, {"user_id": 5}]),
                         [{"user_id": 4}])
        with self.assertRaises(PermissionDenied):
            session.require("user.manage")
        session.end()
        self.assertIsNone(session.person)

    def test_database_manager_singleton_returns_one_instance(self):
        self.assertIs(DatabaseManager.get_instance(), DatabaseManager.get_instance())


class BootstrapSecurityTests(unittest.TestCase):
    def test_initial_admin_uses_hashed_password_and_transaction(self):
        role_repository = unittest.mock.Mock()
        role_repository.find_by_name.return_value = {"role_id": 1}
        user_repository = unittest.mock.Mock()
        user_repository.count_by_role.return_value = 0
        user_repository.create.return_value = 7
        db_manager = unittest.mock.Mock()

        @contextmanager
        def transaction():
            yield object()

        db_manager.get_instance.return_value.transaction.return_value = transaction()
        with patch.object(bootstrap, "RoleRepository", return_value=role_repository), \
                patch.object(bootstrap, "UserRepository", return_value=user_repository), \
                patch.object(bootstrap, "DatabaseManager", db_manager), \
                patch.object(bootstrap, "AuditLogger"):
            result = bootstrap.create_initial_admin("owner", "a-long-password", "System Owner")

        self.assertEqual(result, 7)
        saved_hash = user_repository.create.call_args.args[1]
        self.assertNotEqual(saved_hash, "a-long-password")
        self.assertTrue(verify_password("a-long-password", saved_hash))
        self.assertTrue(PasswordCredentials(saved_hash).verifies("a-long-password"))
        self.assertFalse(PasswordCredentials(saved_hash).verifies("wrong-password"))
        db_manager.get_instance.return_value.transaction.assert_called_once()

    def test_initial_admin_rejects_short_password_before_database_access(self):
        with self.assertRaises(ValidationError):
            bootstrap.create_initial_admin("owner", "short", "System Owner")


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.db = StubDatabase()

    def repository(self, repository_type):
        instance = repository_type()
        instance.db = self.db
        return instance

    def assert_query_success_and_failure(self, repository_type, method, *args):
        repo = self.repository(repository_type)
        self.assertEqual(getattr(repo, method)(*args), [])
        self.db.error = DatabaseError("test database failure")
        with self.assertRaises(DatabaseError):
            getattr(repo, method)(*args)

    def test_role_repository(self):
        repo = self.repository(RoleRepository)
        self.db.rows = [{"role_name": "Staff"}]
        self.assertEqual(repo.find_by_name("Staff"), {"role_name": "Staff"})
        self.assertEqual(self.db.calls[-1][2], ("Staff",))
        self.db.error = DatabaseError("offline")
        with self.assertRaises(DatabaseError):
            repo.find_by_name("Staff")

    def test_user_repository(self):
        repo = self.repository(UserRepository)
        self.db.rows = [{"username": "sample"}]
        self.assertEqual(repo.find_by_username("sample"), {"username": "sample"})
        self.assertEqual(self.db.calls[-1][2], ("sample",))
        self.db.error = DatabaseError("offline")
        with self.assertRaises(DatabaseError):
            repo.find_by_username("sample")

    def test_category_repository(self):
        self.assert_query_success_and_failure(CategoryRepository, "find_all_with_counts")

    def test_product_repository(self):
        repo = self.repository(ProductRepository)
        self.assertEqual(repo.search("50%"), [])
        self.assertIn("%s", self.db.calls[-1][1])
        self.assertIn(r"%50\%%", self.db.calls[-1][2])
        self.db.error = DatabaseError("offline")
        with self.assertRaises(DatabaseError):
            repo.search("50%")

    def test_transaction_repository(self):
        self.assert_query_success_and_failure(TransactionRepository, "find_by_filter")

    def test_audit_repository(self):
        self.assert_query_success_and_failure(AuditLogRepository, "find_by_filter")


if __name__ == "__main__":
    unittest.main()
