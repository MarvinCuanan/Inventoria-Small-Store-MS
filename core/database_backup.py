"""Create and restore versioned JSON backups of the Inventoria database."""
from __future__ import annotations

import base64
import json
from datetime import date, datetime, time
from decimal import Decimal

import mysql.connector

import config
from core.database import DatabaseManager
from core.errors import AppError


BACKUP_FORMAT = "inventoria-database-backup"
BACKUP_VERSION = 1
_BINARY_MARKER = "__inventoria_binary__"


def _json_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {_BINARY_MARKER: base64.b64encode(value).decode("ascii")}
    raise TypeError(f"Unsupported database value: {type(value).__name__}")


def _restore_value(value):
    if isinstance(value, dict) and set(value) == {_BINARY_MARKER}:
        try:
            return base64.b64decode(value[_BINARY_MARKER], validate=True)
        except (ValueError, TypeError) as exc:
            raise AppError("The backup contains invalid binary data.") from exc
    return value


class DatabaseBackup:
    def __init__(self):
        self.db = DatabaseManager.get_instance()

    def create(self, path):
        connection = self.db.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            connection.start_transaction(isolation_level="REPEATABLE READ", consistent_snapshot=True,
                                         readonly=True)
            tables = self._table_names(cursor)
            payload = {
                "format": BACKUP_FORMAT,
                "version": BACKUP_VERSION,
                "database": config.DB_NAME,
                "backed_up_at": datetime.now().isoformat(timespec="seconds"),
                "tables": {},
            }
            for table in tables:
                columns = self._columns(cursor, table)
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                payload["tables"][table] = {
                    "columns": columns,
                    "rows": [[row[column] for column in columns] for row in rows],
                }
            connection.commit()
        except mysql.connector.Error as exc:
            self._rollback(connection)
            raise AppError(DatabaseManager._friendly(exc)) from exc
        except Exception:
            self._rollback(connection)
            raise
        finally:
            cursor.close()

        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, default=_json_value)
                handle.write("\n")
        except OSError:
            raise

    def restore(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise

        connection = self.db.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            tables = self._table_names(cursor)
            self._validate_payload(payload, tables, cursor)
            connection.start_transaction()
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in tables:
                cursor.execute(f"DELETE FROM `{table}`")
            for table in tables:
                data = payload["tables"][table]
                columns = data["columns"]
                if not data["rows"]:
                    continue
                column_sql = ", ".join(f"`{column}`" for column in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                sql = f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})"
                values = [tuple(_restore_value(value) for value in row) for row in data["rows"]]
                cursor.executemany(sql, values)
            connection.commit()
        except mysql.connector.Error as exc:
            self._rollback(connection)
            raise AppError(DatabaseManager._friendly(exc)) from exc
        except Exception:
            self._rollback(connection)
            raise
        finally:
            try:
                cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            finally:
                cursor.close()

    @staticmethod
    def _table_names(cursor):
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME",
            (config.DB_NAME,),
        )
        return [row["TABLE_NAME"] for row in cursor.fetchall()]

    @staticmethod
    def _columns(cursor, table):
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
            (config.DB_NAME, table),
        )
        return [row["COLUMN_NAME"] for row in cursor.fetchall()]

    def _validate_payload(self, payload, tables, cursor):
        if not isinstance(payload, dict) or (
                payload.get("format") != BACKUP_FORMAT
                or payload.get("version") != BACKUP_VERSION
                or payload.get("database") != config.DB_NAME):
            raise AppError("This is not a compatible Inventoria database backup.")
        saved_tables = payload.get("tables")
        if not isinstance(saved_tables, dict) or set(saved_tables) != set(tables):
            raise AppError("The backup tables do not match this database. Restore was cancelled.")
        for table in tables:
            data = saved_tables[table]
            columns = self._columns(cursor, table)
            if not isinstance(data, dict) or data.get("columns") != columns:
                raise AppError(f"The backup structure for '{table}' does not match this database.")
            rows = data.get("rows")
            if not isinstance(rows, list) or any(
                    not isinstance(row, list) or len(row) != len(columns) for row in rows):
                raise AppError(f"The backup data for '{table}' is invalid.")

    @staticmethod
    def _rollback(connection):
        try:
            connection.rollback()
        except mysql.connector.Error:
            pass
