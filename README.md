# Inventoria – Business Management System
Python 3 · Tkinter · MySQL/MariaDB (XAMPP).

## 1. Set up (once)
1. Install **Python 3.10+** from python.org (tick *Add Python to PATH*; the installer includes Tkinter).
2. Open the **XAMPP Control Panel** → click **Start** next to **MySQL** (Apache is only needed if you want phpMyAdmin).
3. In this folder, open a terminal and run:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python setup_database.py
   ```
   Setup creates `inventoria_db`, its tables and permissions. If no Admin exists, it prompts for an administrator username and full name, then asks for a password without displaying or saving it. The password must be at least 12 characters. Answer `y` to load sample products.
   If you import `database/inventoria_schema.sql` using phpMyAdmin, run `python setup_database.py` afterward to create the first Admin securely.
4. Start the app: `python main.py` (or double-click `run_inventoria.bat`).

If your MySQL has a password or another port, edit `DB_CONFIG` in `config.py`.

Run automated tests with `python -m unittest discover -s tests -v`. The suite covers domain rules, repository parameterization/error propagation, validation, authentication and service workflows. The active application is launched by `main.py`; `setup_db.py` is a compatibility entry point to the same setup flow.

## Product specifications
Each product needs a **Specification / selling unit**, such as `1 sack (50 kg)`,
`1 bag (5 kg)`, or `1 bottle (500 ml)`. Stock quantities count those selling units:
for example, a stock quantity of `3` for `Rice` with specification `1 sack (50 kg)`
means **3 sacks**, not 3 kilograms. The specification appears in product search,
stock selection, transactions, reports, and exported CSVs. Products with the same
name can have different specifications (for example, 1 kg and 5 kg rice bags).

When an existing installation starts, the app adds the specification column to its
database automatically; existing products are kept and can be updated from Products
to enter their specifications.

## 2. Who can do what
| Feature | Admin | Staff |
|---|:--:|:--:|
| Login, create own account (self sign-up creates **Staff**) | ✔ | ✔ |
| Dashboard + low-stock alert | ✔ | ✔ |
| View / search products | ✔ | ✔ |
| Add, edit, delete (soft) / restore products, manage categories | ✔ | – |
| Stock In and Stock Out | ✔ | ✔ |
| Transactions | all users, filter by user | **own only** |
| Inventory reports + CSV export | ✔ | – |
| Users: add, change role, activate/deactivate, reset password | ✔ | – |
| Role permissions editor, Audit log | ✔ | – |

Permissions live in the `roles` / `permissions` / `role_permissions` tables, so the Admin can change what Staff may do (Users → *Role permissions*).

## Database backups
Admins can create or restore a database backup from **Users → Backup / Restore**.
Backups are versioned JSON files containing the database records, including user
password hashes and audit history, so store them somewhere private. Restoring
replaces the current database contents and requires a matching database schema;
make a fresh backup first if you may need to recover the current data.

## 3. Built-in safeguards
* Passwords are salted PBKDF2-HMAC-SHA256 hashes; administrator and newly created account passwords must be at least 12 characters. Five wrong logins lock that username for 60 s.
* Stock Out cannot exceed available stock; stock change + transaction + audit log are saved in one all-or-nothing database transaction with a row lock.
* "Delete" is a soft delete – history keeps its product names. Stock levels can only change through Stock In/Out so the ledger always matches.
* The last active Admin cannot be demoted or deactivated; nobody can deactivate or re-role themselves.
* Every login, logout, create, change and delete is recorded in the database Audit Log (before / after values). Application diagnostics are written separately to `inventoria.log`, rotated at 1 MB with five backups.

## 4. How the code matches your diagrams
| Diagram | Where |
|---|---|
| ERD | `database/inventoria_schema.sql` (table names are lowercase) |
| DFD processes 1.0–7.0 | `controllers.py` (Auth, UserManagement, Product/Stock, Transaction, Report, Dashboard, AuditLog) |
| UML – Presentation layer | `ui/` screens + `controllers.py`, `SessionManager` (`core/session.py`), `Validator`, `AuditLogger` |
| UML – Data access layer | `repositories.py`, `DatabaseManager` Singleton (`core/database.py`) |
| Domain abstraction / polymorphism | `Person`, `Admin`, `Staff`, and `StockLevel` (`core/domain.py`) |
| Automated tests | `tests/` (`python -m unittest discover -s tests -v`) |

`Person` is an abstract base class with Admin and Staff implementations that override record visibility; the transaction controller invokes this behavior through the base-class reference. `PasswordCredentials` keeps password hashes behind a read-only property and verifies them without exposing plaintext. `StockLevel` validates quantities through a property setter. Repository classes isolate SQL from controllers and Tkinter screens.

The `app/` package is a retained legacy service-test implementation; it is not launched by `main.py`. Use the root-level `core/`, `controllers.py`, `repositories.py`, and `ui/` as the active system.

## 5. Troubleshooting
* *"Cannot reach MySQL"* → start MySQL in XAMPP. *"Access denied"* → fix `DB_CONFIG` in `config.py`.
* Errors you didn't expect are written to `inventoria.log`.
