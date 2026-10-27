"""DatabaseManager - Singleton wrapper around one MySQL connection (XAMPP)."""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error as MySQLError

import config
from core.errors import AppError, DatabaseError, ValidationError

log = logging.getLogger("inventoria")


class DatabaseManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._conn = None

    @classmethod
    def get_instance(cls) -> "DatabaseManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- connection ---------------------------------------------------
    def get_connection(self):
        try:
            if self._conn is None or not self._conn.is_connected():
                self._conn = mysql.connector.connect(
                    **config.DB_CONFIG, autocommit=True, charset="utf8mb4", connection_timeout=5)
            else:
                self._conn.ping(reconnect=True, attempts=2, delay=1)
            return self._conn
        except MySQLError as exc:
            log.exception("Cannot connect")
            raise DatabaseError(self._friendly(exc)) from exc

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except MySQLError:
            log.exception("Could not close the MySQL connection cleanly")
        finally:
            self._conn = None

    @staticmethod
    def _friendly(exc: MySQLError) -> str:
        code = getattr(exc, "errno", None)
        if code in (2002, 2003, 2006, 2013):
            return ("Cannot reach MySQL.\nOpen the XAMPP Control Panel and make sure MySQL is started, "
                    "then try again.")
        if code == 1049:
            return (f"Database '{config.DB_NAME}' was not found.\nRun  python setup_database.py  "
                    "or import database/inventoria_schema.sql in phpMyAdmin.")
        if code == 1146:
            return "Database tables are missing.\nRun  python setup_database.py  to create them."
        if code == 1045:
            return "MySQL refused the login. Check the user and password in config.py (DB_CONFIG)."
        return f"Database error: {exc}"

    # ---- queries ------------------------------------------------------
    def _run(self, sql, params, cursor, fetch):
        try:
            if cursor is not None:
                cursor.execute(sql, params or ())
                return cursor.fetchall() if fetch else (cursor.rowcount, cursor.lastrowid)
            cur = self.get_connection().cursor(dictionary=True)
            try:
                cur.execute(sql, params or ())
                return cur.fetchall() if fetch else (cur.rowcount, cur.lastrowid)
            finally:
                cur.close()
        except AppError:
            raise
        except MySQLError as exc:
            if exc.errno == 1062:
                raise ValidationError("That value already exists (duplicate entry).") from exc
            if exc.errno in (1451, 1452):
                raise ValidationError("This record is linked to other data and cannot be changed or removed.") from exc
            if exc.errno in (3819, 4025):
                raise ValidationError("The value was rejected by a database rule (check the numbers entered).") from exc
            log.exception("SQL failed: %s", sql)
            raise DatabaseError(self._friendly(exc)) from exc

    def query(self, sql, params=None, cursor=None) -> list[dict]:
        """SELECT -> list of dict rows."""
        return self._run(sql, params, cursor, fetch=True)

    def execute(self, sql, params=None, cursor=None) -> tuple[int, int]:
        """INSERT/UPDATE/DELETE -> (affected_rows, last_insert_id)."""
        return self._run(sql, params, cursor, fetch=False)

    @contextmanager
    def transaction(self):
        """All-or-nothing block:  with db.transaction() as cur: ...  (rolls back on any error)."""
        conn = self.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            yield cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except MySQLError:
                pass
            raise
        finally:
            cur.close()
