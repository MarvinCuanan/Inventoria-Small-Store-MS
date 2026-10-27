"""First-run setup: creates the database, tables, seed data and the default admin."""
import re

import mysql.connector

from .config import DB_CONFIG, DB_NAME, SCHEMA_FILE
from .database import Database
from .errors import DatabaseError


def _statements(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"--[^\n]*", "", text)           # strip comments
    for raw in text.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue
        head = stmt.split(None, 2)
        first = " ".join(head[:2]).upper()
        if first == "CREATE DATABASE" or head[0].upper() == "USE":
            continue                                # database is created from config
        yield stmt


def ensure_database() -> None:
    """Idempotent: safe to call on every start-up."""
    try:
        conn = mysql.connector.connect(connection_timeout=5, **DB_CONFIG)
    except mysql.connector.Error as exc:
        raise DatabaseError(Database._friendly(exc)) from exc
    try:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"USE `{DB_NAME}`")
        for stmt in _statements(SCHEMA_FILE):
            cur.execute(stmt)
        conn.commit()
        cur.close()
    except mysql.connector.Error as exc:
        raise DatabaseError(f"Could not create the database tables: {exc}") from exc
    finally:
        conn.close()
