"""Database bootstrap checks and explicit initial administrator creation."""
from core.audit import AuditLogger
from core.database import DatabaseManager
from core.errors import AppError, ValidationError
from core.security import hash_password
from repositories import RoleRepository, UserRepository


def ensure_product_specification() -> None:
    """Add the optional-at-database-level specification field to older installations."""
    db = DatabaseManager.get_instance()
    columns = db.query("SHOW COLUMNS FROM products LIKE %s", ("specification",))
    if not columns:
        db.execute("ALTER TABLE products ADD COLUMN specification VARCHAR(255) NOT NULL DEFAULT '' "
                   "AFTER product_name")


def ensure_admin_exists() -> None:
    """Fail with setup instructions when the database has no administrator."""
    roles, users = RoleRepository(), UserRepository()
    admin_role = roles.find_by_name("Admin")
    if admin_role is None:
        raise AppError("The database is empty. Run  python setup_database.py  first "
                       "(or import database/inventoria_schema.sql in phpMyAdmin).")
    if users.count_by_role(admin_role["role_id"]) > 0:
        return
    raise AppError("No administrator account exists. Run  python setup_database.py  "
                   "to create one securely.")


def create_initial_admin(username: str, password: str, full_name: str) -> int:
    """Create the first administrator from credentials entered during setup."""
    username, full_name = username.strip(), full_name.strip()
    if not username or not full_name:
        raise ValidationError("Administrator username and full name are required.")
    if len(password) < 12:
        raise ValidationError("Administrator password must be at least 12 characters.")
    roles, users = RoleRepository(), UserRepository()
    admin_role = roles.find_by_name("Admin")
    if admin_role is None:
        raise ValidationError("The Admin role is missing. Import the database schema first.")
    if users.count_by_role(admin_role["role_id"]) > 0:
        raise ValidationError("An administrator already exists; no new account was created.")
    with DatabaseManager.get_instance().transaction() as cur:
        uid = users.create(username, hash_password(password), admin_role["role_id"], full_name, cursor=cur)
        AuditLogger().log("INSERT", "users", uid, None,
                          {"username": username, "role": "Admin", "note": "initial administrator"},
                          cursor=cur, user_id=uid)
    return uid
