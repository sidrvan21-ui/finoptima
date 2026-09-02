DROP TABLE IF EXISTS cloud_line_items CASCADE;
DROP TABLE IF EXISTS saas_contracts CASCADE;
DROP TABLE IF EXISTS monthly_budgets CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS legal_entities CASCADE;

CREATE TABLE legal_entities (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    country TEXT NOT NULL,
    currency TEXT NOT NULL
);

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES legal_entities(id),
    name TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    UNIQUE (entity_id, name)
);

CREATE TABLE monthly_budgets (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    year_month TEXT NOT NULL,
    limit_usd DOUBLE PRECISION NOT NULL,
    UNIQUE (department_id, year_month)
);

CREATE TABLE cloud_line_items (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    year_month TEXT NOT NULL,
    service TEXT NOT NULL,
    environment TEXT NOT NULL,
    region TEXT NOT NULL,
    amount_usd DOUBLE PRECISION NOT NULL
);

CREATE TABLE saas_contracts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    vendor TEXT NOT NULL,
    arr_usd DOUBLE PRECISION NOT NULL,
    last_active_days_ago INTEGER NOT NULL,
    owner_email TEXT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    renewal_year_month TEXT NOT NULL
);

CREATE INDEX idx_cloud_dept_month ON cloud_line_items (department_id, year_month);
CREATE INDEX idx_cloud_month ON cloud_line_items (year_month);
CREATE INDEX idx_saas_dept ON saas_contracts (department_id);
CREATE INDEX idx_saas_idle ON saas_contracts (last_active_days_ago);
CREATE INDEX idx_budget_dept_month ON monthly_budgets (department_id, year_month);
