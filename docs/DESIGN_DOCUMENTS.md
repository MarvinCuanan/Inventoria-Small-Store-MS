# Inventoria Design Documents

These are editable diagram sources for the design-document deliverables. Render the labeled Mermaid diagrams in a Mermaid-compatible editor, then export/print each diagram to PDF for the final submission.

## 1. System flowchart

```mermaid
flowchart TD
    A([Start]) --> B[Connect to MySQL and verify schema]
    B --> C{Administrator exists?}
    C -- No --> D[Run setup_database.py and create initial administrator]
    D --> B
    C -- Yes --> E[Show login screen]
    E --> F{Credentials valid and account active?}
    F -- No --> E
    F -- Yes --> G[Load role permissions and show authorized modules]
    G --> H{Selected action}
    H --> I[Validate input]
    I --> J{Input valid?}
    J -- No --> K[Display validation error]
    K --> G
    J -- Yes --> L[Controller invokes repository]
    L --> M[(MySQL database)]
    M --> N[Display result; audit data changes]
    N --> G
    G --> O[Logout or exit]
    O --> P([Close shared database connection])
```

## 2. Context diagram

```mermaid
flowchart LR
    Admin[Administrator] -->|credentials, inventory/user actions, filters| System((Inventoria))
    Staff[Staff] -->|credentials, stock movement, product/transaction queries| System
    System -->|screens, reports, validation/errors| Admin
    System -->|screens, own transactions, validation/errors| Staff
    System <-->|parameterized SQL / records| DB[(XAMPP MySQL/MariaDB)]
    System -->|rotating diagnostics| Log[(inventoria.log)]
    System -->|CSV report/transaction export| CSV[CSV files]
    Setup[Setup operator] -->|initial admin credentials, hidden password entry| System
```

## 3. Level-1 data-flow diagram

```mermaid
flowchart LR
    Admin[Administrator]
    Staff[Staff]
    P1((1. Authenticate and authorize))
    P2((2. Manage users and permissions))
    P3((3. Manage products and categories))
    P4((4. Record stock movements))
    P5((5. Search transactions))
    P6((6. Generate reports and exports))
    P7((7. Review audit events))
    D1[(Users, roles, permissions)]
    D2[(Products, categories)]
    D3[(Transactions)]
    D4[(Audit logs)]
    D5[(Application log)]
    Admin --> P1
    Staff --> P1
    P1 <--> D1
    P1 --> P2
    P2 <--> D1
    P2 --> D4
    Admin --> P3
    Staff --> P3
    P3 <--> D2
    P3 --> D4
    Admin --> P4
    Staff --> P4
    P4 <--> D2
    P4 --> D3
    P4 --> D4
    Admin --> P5
    Staff --> P5
    P5 --> D3
    Admin --> P6
    P6 --> D2
    P6 --> D3
    P6 --> Export[On-screen report / CSV]
    Admin --> P7
    P7 --> D4
    P1 -. unexpected errors .-> D5
    P2 -. unexpected errors .-> D5
    P3 -. unexpected errors .-> D5
    P4 -. unexpected errors .-> D5
```

## 4. Level-2 DFD: stock movement

```mermaid
flowchart TD
    User[Authorized Admin or Staff] --> A[4.1 Choose product, IN/OUT, quantity]
    A --> B[4.2 Validate permission and input]
    B --> C{Valid?}
    C -- No --> Error[Show safe error message]
    C -- Yes --> D[4.3 Begin database transaction]
    D --> E[4.4 Lock and read product stock]
    E <--> Products[(Products)]
    E --> F{Active product and enough stock?}
    F -- No --> R[Rollback transaction]
    R --> Error
    F -- Yes --> G[4.5 Update stock quantity]
    G --> Products
    G --> H[4.6 Insert transaction row]
    H --> Transactions[(Transactions)]
    H --> I[4.7 Insert audit event]
    I --> Audit[(Audit logs)]
    I --> J[4.8 Commit transaction]
    J --> K[Show updated stock]
```

## 5. UML class diagram

```mermaid
classDiagram
    class Person {
        <<abstract>>
        -int _user_id
        -str _username
        +user_id int
        +username str
        +visible_records(records) list
    }
    class Admin {
        +visible_records(records) list
    }
    class Staff {
        +visible_records(records) list
    }
    class PasswordCredentials {
        -str _password_hash
        +password_hash str
        +verifies(password) bool
    }
    class StockLevel {
        -int _quantity
        +quantity int
        +increase(amount) int
        +decrease(amount) int
    }
    class SessionManager {
        +current_user dict
        +permissions set
        +person Person
        +start(user, permissions)
        +require(permission)
    }
    class BaseController {
        +session SessionManager
        +require(permission)
    }
    class TransactionController {
        +list_transactions(filters)
    }
    class DatabaseManager {
        -connection
        +get_instance()
        +query(sql, params)
        +execute(sql, params)
        +transaction()
    }
    class BaseRepository {
        +db DatabaseManager
    }
    class UserRepository
    class ProductRepository
    class CategoryRepository
    class TransactionRepository
    class AuditLogRepository
    class MainWindow
    class Page

    Person <|-- Admin
    Person <|-- Staff
    SessionManager o-- Person
    BaseController <|-- TransactionController
    TransactionController --> TransactionRepository
    TransactionController --> Person : polymorphic visibility
    BaseRepository <|-- UserRepository
    BaseRepository <|-- ProductRepository
    BaseRepository <|-- CategoryRepository
    BaseRepository <|-- TransactionRepository
    BaseRepository <|-- AuditLogRepository
    BaseRepository --> DatabaseManager
    MainWindow o-- Page
```

## 6. Entity-relationship diagram

```mermaid
erDiagram
    ROLES ||--o{ USERS : assigns
    USERS ||--o| USER_PROFILES : describes
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : includes
    CATEGORIES ||--o{ PRODUCTS : groups
    PRODUCTS ||--o{ TRANSACTIONS : records
    USERS ||--o{ TRANSACTIONS : performs
    USERS ||--o{ AUDIT_LOGS : generates

    ROLES {
        int role_id PK
        varchar role_name UK
        varchar description
    }
    PERMISSIONS {
        int permission_id PK
        varchar permission_name UK
        varchar description
    }
    ROLE_PERMISSIONS {
        int role_id PK, FK
        int permission_id PK, FK
    }
    USERS {
        int user_id PK
        int role_id FK
        varchar username UK
        varchar password_hash
        boolean is_active
    }
    USER_PROFILES {
        int user_id PK, FK
        varchar full_name
        varchar email UK
        varchar contact_no
    }
    CATEGORIES {
        int category_id PK
        varchar category_name UK
        varchar description
    }
    PRODUCTS {
        int product_id PK
        int category_id FK
        varchar sku UK
        varchar product_name
        varchar specification
        decimal price
        int stock_quantity
        int low_stock_threshold
        boolean is_active
    }
    TRANSACTIONS {
        int transaction_id PK
        int product_id FK
        int user_id FK
        decimal unit_price
        enum transaction_type
        int quantity
        datetime transaction_date
    }
    AUDIT_LOGS {
        int log_id PK
        int user_id FK
        varchar action
        varchar table_affected
        int record_id
        json old_values
        json new_values
        datetime created_at
    }
```

The authoritative DDL, indexes, constraints, seed roles, and seed permissions are in `database/inventoria_schema.sql`.
