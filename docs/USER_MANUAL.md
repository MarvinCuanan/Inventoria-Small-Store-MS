# Inventoria User Manual

## 1. Requirements

- Windows 10/11
- Python 3.10 or later, with Tkinter
- XAMPP with its MySQL/MariaDB service
- `mysql-connector-python` (installed from `requirements.txt`)

## 2. Installation and first run

1. Install Python and XAMPP. In the XAMPP Control Panel, start **MySQL**. Apache is only needed to use phpMyAdmin.
2. Open PowerShell in the project folder and create the virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Configure the MySQL host, port, username, and password in `config.py` if they differ from the XAMPP defaults.
4. Create the database and first administrator:

   ```powershell
   python setup_database.py
   ```

   The setup prompts for an administrator username, full name, and password. Password input is hidden, the password is never printed or written to a file, and it must be 12-128 characters. If importing `database/inventoria_schema.sql` through phpMyAdmin, run this setup command afterward to create the first administrator.
5. Launch the application:

   ```powershell
   python main.py
   ```

   Or use `run_inventoria.bat` after creating the virtual environment.

## 3. Sign-in and roles

Enter the administrator credentials created during setup. Staff can create an account from the login screen; self-registered accounts receive the Staff role. Administrators can manage accounts, assign roles, and edit role permissions from **Users**.

The navigation and controller permission checks restrict administrative actions. Staff may view/search products, record stock movements, and view their own transactions. Administrators can manage products, users, reports, audit logs, and all transactions.

## 4. Common tasks

### Find products

Open **Products**, type a product name, specification, SKU, or category in the search field, then select a row to edit it if permitted.

### Add or update a product

Administrators select **+ Add Product** or **Edit**. Enter the product name, selling-unit specification, SKU (optional), category, price, and low-stock threshold. Opening stock is recorded as a stock-in transaction. Product stock is intentionally not editable in the product form.

### Record stock in/out

Open **Stock**, choose a product and movement type, enter a positive whole-number quantity, then submit. Stock-out cannot exceed the available quantity. Each movement updates stock, creates a transaction, and writes an audit entry in one database transaction.

### Search and export transactions

Open **Transaction Records**, choose filters, and select **Search**. Administrators can filter by user; Staff only see their own records. Use **Export CSV** to save the visible filtered results.

### Generate and export a report

Administrators open **Reports**, choose a date range, and select **Generate**. The report shows stock totals, movement totals, stock value, and low-stock status. Select **Export CSV** to save it.

### Manage users and audit history

Administrators use **Users** to add accounts, change roles, activate/deactivate accounts, reset passwords, change permissions, or create/restore database backups. Use **Audit Log** to review recorded changes.

## 5. Tests

Run the unit tests from the project folder with:

```powershell
python -m unittest discover -s tests -v
```

The tests cover active domain objects, repository success and failure paths, password handling, validators, and legacy service logic. MySQL and a graphical display are not required for the unit suite.

## 6. Data, logs, and security

- MySQL/MariaDB is the primary store. The SQL schema is in `database/inventoria_schema.sql`.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes.
- Application diagnostics are written to `inventoria.log`, rotated at 1 MB with five backups.
- Audit events are stored separately in MySQL.
- Backup JSON includes password hashes and business records; keep it private.

## 7. Troubleshooting

- **Cannot reach MySQL:** start MySQL in XAMPP and verify `DB_CONFIG` in `config.py`.
- **Missing database or tables:** run `python setup_database.py`.
- **No administrator exists:** run `python setup_database.py` and complete the hidden-password prompt.
- **Access denied:** ask an administrator to review your account role and permissions.
- **Unexpected application error:** review `inventoria.log`; the UI also reports the error.
