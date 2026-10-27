-- ============================================================
--  Inventoria Business Management System - database schema
--  Target: MySQL / MariaDB (XAMPP + phpMyAdmin)
--  Normalised to 3NF. Safe to run more than once.
--  You can import this file in phpMyAdmin (Import tab) or let
--  the application create everything automatically on first run.
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventoria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE inventoria;

-- ---------- Access control ----------
CREATE TABLE IF NOT EXISTS roles (
    role_id      INT AUTO_INCREMENT PRIMARY KEY,
    role_name    VARCHAR(50)  NOT NULL UNIQUE,
    description  VARCHAR(255) NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS permissions (
    permission_id    INT AUTO_INCREMENT PRIMARY KEY,
    permission_name  VARCHAR(100) NOT NULL UNIQUE,
    description      VARCHAR(255) NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id        INT NOT NULL,
    permission_id  INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_rp_role       FOREIGN KEY (role_id)       REFERENCES roles(role_id)             ON DELETE CASCADE,
    CONSTRAINT fk_rp_permission FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id     INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(100) NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,              -- salted PBKDF2 hash, never plain text
    role_id     INT          NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------- Inventory ----------
CREATE TABLE IF NOT EXISTS categories (
    category_id    INT AUTO_INCREMENT PRIMARY KEY,
    category_name  VARCHAR(100) NOT NULL UNIQUE,
    description    VARCHAR(255) NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
    product_id           INT AUTO_INCREMENT PRIMARY KEY,
    product_name         VARCHAR(150)  NOT NULL UNIQUE,
    category_id          INT           NULL,
    price                DECIMAL(10,2) NOT NULL,
    stock_quantity       INT           NOT NULL DEFAULT 0,
    low_stock_threshold  INT           NOT NULL DEFAULT 10,
    is_active            TINYINT(1)    NOT NULL DEFAULT 1,   -- 0 = deleted (kept for history)
    created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock_quantity >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id    INT AUTO_INCREMENT PRIMARY KEY,
    product_id        INT          NOT NULL,
    user_id           INT          NOT NULL,
    transaction_type  ENUM('Stock In','Stock Out') NOT NULL,
    quantity          INT          NOT NULL,
    transaction_date  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks           VARCHAR(255) NULL,
    CONSTRAINT fk_tx_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    CONSTRAINT fk_tx_user    FOREIGN KEY (user_id)    REFERENCES users(user_id)       ON DELETE RESTRICT,
    CONSTRAINT chk_tx_quantity CHECK (quantity > 0),
    INDEX idx_tx_date (transaction_date),
    INDEX idx_tx_product (product_id)
) ENGINE=InnoDB;

-- ---------- Auditing ----------
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT          NULL,
    action          VARCHAR(10)  NOT NULL,
    table_affected  VARCHAR(100) NULL,
    record_id       INT          NULL,
    old_values      TEXT         NULL,
    new_values      TEXT         NULL,
    ip_address      VARCHAR(45)  NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB;

-- ---------- Seed data (idempotent) ----------
INSERT IGNORE INTO roles (role_name, description) VALUES
    ('Admin', 'Full access to every feature'),
    ('Staff', 'Day-to-day inventory work, cannot delete products');

INSERT IGNORE INTO permissions (permission_name, description) VALUES
    ('product.view',    'View products'),
    ('product.add',     'Add products'),
    ('product.edit',    'Edit products'),
    ('product.delete',  'Delete products'),
    ('stock.add',       'Add stock (Stock In)'),
    ('stock.remove',    'Remove stock (Stock Out)'),
    ('transaction.view','View transaction records'),
    ('report.view',     'Generate inventory reports'),
    ('user.manage',     'Manage user accounts');

INSERT IGNORE INTO role_permissions (role_id, permission_id)
    SELECT r.role_id, p.permission_id
    FROM roles r CROSS JOIN permissions p
    WHERE r.role_name = 'Admin';

INSERT IGNORE INTO role_permissions (role_id, permission_id)
    SELECT r.role_id, p.permission_id
    FROM roles r CROSS JOIN permissions p
    WHERE r.role_name = 'Staff'
      AND p.permission_name NOT IN ('product.delete', 'user.manage');

INSERT IGNORE INTO categories (category_name, description) VALUES
    ('Groceries',  'Rice, noodles, canned goods and pantry items'),
    ('Beverages',  'Softdrinks, water, juices and coffee'),
    ('Household',  'Soap, detergent and cleaning supplies'),
    ('Bakery',     'Bread and pastries'),
    ('Others',     'Anything that does not fit elsewhere');
