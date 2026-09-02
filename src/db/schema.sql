CREATE TABLE legal_entities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    country TEXT NOT NULL,
    currency TEXT NOT NULL
);

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    UNIQUE (entity_id, name),
    FOREIGN KEY (entity_id) REFERENCES legal_entities(id)
);

CREATE TABLE monthly_budgets (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL,
    year_month TEXT NOT NULL,
    limit_usd REAL NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE cloud_line_items (
    id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL,
    year_month TEXT NOT NULL,
    service TEXT NOT NULL,
    environment TEXT NOT NULL,
    region TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE saas_contracts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    vendor TEXT NOT NULL,
    arr_usd REAL NOT NULL,
    last_active_days_ago INTEGER NOT NULL,
    owner_email TEXT NOT NULL,
    risk_score REAL NOT NULL,
    renewal_year_month TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
