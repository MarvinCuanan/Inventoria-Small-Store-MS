-- ============================================================
-- Inventoria Business Management System
-- MySQL / MariaDB (XAMPP) schema  -  normalised to 3NF
-- Import in phpMyAdmin (Import tab) or run:  python setup_database.py
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventoria_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE inventoria_db;

-- ---------- Roles & permissions (RBAC) ----------
CREATE TABLE IF NOT EXISTS roles (
    role_id     INT AUTO_INCREMENT PRIMARY KEY,
    role_name   VARCHAR(50)  NOT NULL UNIQUE,
    description VARCHAR(255) NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS permissions (
    permission_id   INT AUTO_INCREMENT PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL UNIQUE,
    description     VARCHAR(255) NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- many-to-many bridge: Roles 1..* Role_Permissions *..1 Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INT NOT NULL,
    permission_id INT NOT NULL,
    granted_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_rp_role  FOREIGN KEY (role_id)       REFERENCES roles(role_id)             ON DELETE CASCADE,
    CONSTRAINT fk_rp_perm  FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------- Users ----------
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    role_id       INT NOT NULL,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    last_login_at DATETIME NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(role_id)
) ENGINE=InnoDB;

-- 1:1 with users
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id    INT PRIMARY KEY,
    full_name  VARCHAR(150) NOT NULL,
    email      VARCHAR(150) NULL UNIQUE,
    contact_no VARCHAR(20)  NULL,
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------- Inventory ----------
CREATE TABLE IF NOT EXISTS categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description   VARCHAR(255) NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
    product_id          INT AUTO_INCREMENT PRIMARY KEY,
    category_id         INT NOT NULL,
    sku                 VARCHAR(50)  NOT NULL UNIQUE,
    product_name        VARCHAR(100) NOT NULL,
    specification       VARCHAR(255) NOT NULL DEFAULT '',
    price               DECIMAL(10,2) NOT NULL,
    stock_quantity      INT NOT NULL DEFAULT 0,
    low_stock_threshold INT NOT NULL DEFAULT 10,
    is_active           TINYINT(1) NOT NULL DEFAULT 1,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock_quantity >= 0),
    INDEX idx_products_name (product_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   INT AUTO_INCREMENT PRIMARY KEY,
    product_id       INT NOT NULL,
    user_id          INT NOT NULL,
    unit_price       DECIMAL(10,2) NOT NULL,
    transaction_type ENUM('IN','OUT','ADJUSTMENT') NOT NULL,
    quantity         INT NOT NULL,
    transaction_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks          VARCHAR(255) NULL,
    CONSTRAINT fk_tx_product FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_tx_user    FOREIGN KEY (user_id)    REFERENCES users(user_id),
    CONSTRAINT chk_tx_qty CHECK (quantity > 0),
    INDEX idx_tx_date (transaction_date)
) ENGINE=InnoDB;

-- ---------- Audit trail ----------
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NULL,
    action         ENUM('INSERT','UPDATE','DELETE','LOGIN','LOGOUT') NOT NULL,
    table_affected VARCHAR(64) NULL,
    record_id      INT NULL,
    old_values     JSON NULL,
    new_values     JSON NULL,
    ip_address     VARCHAR(45) NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_audit_date (created_at)
) ENGINE=InnoDB;

-- ---------- Seed data: roles ----------
INSERT IGNORE INTO roles (role_name, description) VALUES
 ('Admin', 'Full control: products, categories, stock, reports, users, roles and audit trail'),
 ('Staff', 'Daily operations: view/search products, record stock in/out, see own transactions');

-- ---------- Seed data: permissions ----------
INSERT IGNORE INTO permissions (permission_name, description) VALUES
 ('dashboard.view',       'View the dashboard'),
 ('product.view',         'View and search products'),
 ('product.add',          'Add new products'),
 ('product.edit',         'Edit product details'),
 ('product.delete',       'Delete (deactivate) and restore products'),
 ('category.manage',      'Add, rename and delete categories'),
 ('stock.in',             'Record stock-in (add stock)'),
 ('stock.out',            'Record stock-out (remove stock)'),
 ('transaction.view_own', 'View own transactions'),
 ('transaction.view_all', 'View everyone''s transactions'),
 ('report.view',          'Generate inventory reports'),
 ('user.manage',          'Manage user accounts, roles and permissions'),
 ('audit.view',           'View the audit trail');

-- Admin gets everything
INSERT IGNORE INTO role_permissions (role_id, permission_id)
 SELECT r.role_id, p.permission_id FROM roles r CROSS JOIN permissions p WHERE r.role_name = 'Admin';

-- Staff gets daily-operation permissions only
INSERT IGNORE INTO role_permissions (role_id, permission_id)
 SELECT r.role_id, p.permission_id FROM roles r CROSS JOIN permissions p
 WHERE r.role_name = 'Staff'
   AND p.permission_name IN ('dashboard.view','product.view','stock.in','stock.out','transaction.view_own');

-- ---------- Seed data: starter categories ----------
INSERT IGNORE INTO categories (category_name, description) VALUES
 ('General',   'Uncategorised items'),
 ('Groceries', 'Rice, noodles, canned goods, bread'),
 ('Beverages', 'Softdrinks, juices, water'),
 ('Household', 'Soap, detergent, cleaning items');
