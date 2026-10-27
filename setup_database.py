"""One-time setup:  creates the inventoria_db database, tables, roles/permissions and the default admin.

1. Start MySQL in the XAMPP Control Panel.
2. Run:  python setup_database.py
"""
import os
import sys
from getpass import getpass

import mysql.connector
from mysql.connector import Error

import config
from core.database import DatabaseManager
from core.errors import AppError
from core.bootstrap import create_initial_admin
from core.validator import Validator

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "inventoria_schema.sql")

# (sku, name, category, price, stock_in, stock_out, alert_level)  -> final stock = in - out
SAMPLE = [
    ("RICE-1KG", "Rice (1kg)", "Groceries", 45, 22, 20, 10),
    ("SOAP-001", "Soap", "Household", 20, 18, 10, 10),
    ("COKE-500", "Coke (500ml)", "Beverages", 35, 20, 15, 10),
    ("BREAD-01", "Bread", "Groceries", 25, 24, 12, 10),
    ("NOOD-001", "Noodles", "Groceries", 18, 38, 18, 10),
    ("SUGAR-1K", "Sugar (1kg)", "Groceries", 70, 40, 8, 10),
    ("OIL-1L", "Cooking Oil (1L)", "Groceries", 95, 30, 6, 8),
    ("WATER-500", "Bottled Water (500ml)", "Beverages", 15, 60, 24, 20),
    ("DETER-500", "Detergent Powder", "Household", 12, 50, 14, 15),
    ("SARD-155", "Canned Sardines", "Groceries", 28, 36, 10, 10),
]


def run_schema():
    with open(SCHEMA, encoding="utf-8") as handle:
        lines = [ln for ln in handle.read().splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    cfg = {k: v for k, v in config.DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**cfg, autocommit=True, connection_timeout=5)
    cur = conn.cursor()
    for statement in statements:
        cur.execute(statement)
    cur.close()
    conn.close()
    from core.bootstrap import ensure_product_specification
    ensure_product_specification()


def seed_sample_data():
    from repositories import CategoryRepository
    db = DatabaseManager.get_instance()
    admins = db.query(
        "SELECT u.user_id FROM users u JOIN roles r ON r.role_id=u.role_id "
        "WHERE r.role_name=%s ORDER BY u.user_id LIMIT 1", ("Admin",))
    if not admins:
        raise AppError("Create an administrator before loading sample data.")
    admin_id = admins[0]["user_id"]
    cats = {c["category_name"]: c["category_id"] for c in CategoryRepository().find_all()}
    for sku, name, cat, price, qty_in, qty_out, alert in SAMPLE:
        if db.query("SELECT 1 AS x FROM products WHERE sku=%s", (sku,)):
            continue
        with db.transaction() as cur:
            _, pid = db.execute(
                "INSERT INTO products (sku, product_name, category_id, price, stock_quantity, low_stock_threshold) "
                "VALUES (%s,%s,%s,%s,%s,%s)", (sku, name, cats[cat], price, qty_in - qty_out, alert), cur)
            db.execute("INSERT INTO transactions (product_id, user_id, unit_price, transaction_type, quantity, "
                       "transaction_date, remarks) VALUES (%s,%s,%s,'IN',%s,NOW() - INTERVAL 5 DAY,'Sample opening stock')",
                       (pid, admin_id, price, qty_in), cur)
            db.execute("INSERT INTO transactions (product_id, user_id, unit_price, transaction_type, quantity, "
                       "transaction_date, remarks) VALUES (%s,%s,%s,'OUT',%s,NOW() - INTERVAL 1 DAY,'Sample sales')",
                       (pid, admin_id, price, qty_out), cur)


def create_admin_if_needed():
    db = DatabaseManager.get_instance()
    admins = db.query(
        "SELECT u.user_id FROM users u JOIN roles r ON r.role_id=u.role_id "
        "WHERE r.role_name=%s LIMIT 1", ("Admin",))
    if admins:
        print("[OK] An administrator account already exists; it was not changed.")
        return

    print("\nCreate the first administrator (password is hidden while typing).")
    username = input("Admin username: ").strip()
    if not Validator.is_valid_username(username):
        raise AppError("Username must be 3-30 characters: letters, numbers, dot or underscore.")
    full_name = input("Admin full name: ").strip()
    password = getpass("Admin password (at least 12 characters): ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise AppError("The passwords do not match.")
    create_initial_admin(username, password, full_name)
    print("[OK] Administrator created. Credentials were not written to a file.")


def main():
    print("Inventoria database setup\n-------------------------")
    try:
        run_schema()
        print("[OK] Database and tables are ready.")
        create_admin_if_needed()
        if input("Add sample products so you can try the system? (y/N): ").strip().lower() == "y":
            seed_sample_data()
            print("[OK] Sample products added.")
    except Error as exc:
        print(f"\n[ERROR] {exc}\nIs MySQL running in the XAMPP Control Panel? Check DB_CONFIG in config.py.")
        sys.exit(1)
    except AppError as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
    print("\nDone. Start the app with:  python main.py")


if __name__ == "__main__":
    main()
