"""Inventoria settings. Edit DB_CONFIG if XAMPP uses a password or a different port."""
import os

APP_NAME = "Inventoria"
APP_SUBTITLE = "Business Management System"

DB_NAME = "inventoria_db"
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",       # XAMPP default
    "password": "",       # XAMPP default is empty
    "database": DB_NAME,
}

CURRENCY = "₱"
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_LOGIN_ATTEMPTS = 5          # wrong passwords allowed ...
LOCKOUT_SECONDS = 60            # ... before the username is locked for this long
MAX_STOCK_MOVEMENT = 100000     # largest quantity for one stock-in / stock-out
DASHBOARD_REFRESH_MS = 30000    # dashboard auto-refresh (30 s)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventoria.log")
