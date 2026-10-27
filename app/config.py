"""Central configuration. Defaults match a fresh XAMPP install.

Change the values here, or override them with environment variables
(INVENTORIA_DB_HOST, INVENTORIA_DB_PORT, INVENTORIA_DB_USER,
INVENTORIA_DB_PASSWORD, INVENTORIA_DB_NAME).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"

DB_NAME = os.getenv("INVENTORIA_DB_NAME", "inventoria")
DB_CONFIG = {
    "host": os.getenv("INVENTORIA_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("INVENTORIA_DB_PORT", "3306")),
    "user": os.getenv("INVENTORIA_DB_USER", "root"),
    "password": os.getenv("INVENTORIA_DB_PASSWORD", ""),  # XAMPP default: empty
}

# Retained for the legacy service-test package; admin accounts are created by setup_database.py.
DEFAULT_LOW_STOCK_THRESHOLD = 10
APP_NAME = "Inventoria"
APP_SUBTITLE = "Business Management System"
