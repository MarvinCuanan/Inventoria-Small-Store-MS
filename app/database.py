"""Singleton database manager (one shared MySQL connection for the whole app)."""
import threading
from contextlib import contextmanager

import mysql.connector
from mysql.connector import errorcode

from .config import DB_CONFIG, DB_NAME
from .errors import DatabaseError, ValidationError


class Database:
    """Singleton: ``Database()`` always returns the same instance."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._conn = None
            return cls._instance

    # ---- connection handling ----
    @property
    def connection(self):
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True, attempts=2, delay=1)
                return self._conn
            except mysql.connector.Error:
                self._conn = None
        try:
            self._conn = mysql.connector.connect(
                database=DB_NAME,
                charset="utf8mb4",
                autocommit=True,
                connection_timeout=5,
                **DB_CONFIG,
            )
        except mysql.connector.Error as exc:
            raise DatabaseError(self._friendly(exc)) from exc
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except mysql.connector.Error:
                pass
            self._conn = None

    # ---- statements ----
    def query(self, sql, params=(), one=False):
        cur = self.connection.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchone() if one else cur.fetchall()
        except mysql.connector.Error as exc:
            raise self._translate(exc) from exc
        finally:
            cur.close()

    def execute(self, sql, params=()):
        """Run INSERT/UPDATE/DELETE. Returns the new auto-increment id (if any)."""
        cur = self.connection.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.lastrowid
        except mysql.connector.Error as exc:
            raise self._translate(exc) from exc
        finally:
            cur.close()

    @contextmanager
    def transaction(self):
        """All statements run on the yielded cursor commit together or not at all."""
        conn = self.connection
        cur = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            yield cur
            conn.commit()
        except mysql.connector.Error as exc:
            self._rollback(conn)
            raise self._translate(exc) from exc
        except BaseException:
            self._rollback(conn)
            raise
        finally:
            cur.close()

    # ---- helpers ----
    @staticmethod
    def _rollback(conn):
        try:
            conn.rollback()
        except mysql.connector.Error:
            pass

    @staticmethod
    def _friendly(exc) -> str:
        errno = getattr(exc, "errno", None)
        if errno == errorcode.ER_ACCESS_DENIED_ERROR:
            return "MySQL rejected the username or password. Check DB_CONFIG in app/config.py."
        if errno == errorcode.CR_CONN_HOST_ERROR or errno == 2003 or errno == 2002:
            return ("Cannot reach MySQL. Open the XAMPP Control Panel and click Start "
                    "next to MySQL, then try again.")
        return f"Database error: {exc}"

    def _translate(self, exc):
        if isinstance(exc, mysql.connector.IntegrityError):
            return ValidationError("That record already exists or conflicts with existing data.")
        return DatabaseError(self._friendly(exc))
