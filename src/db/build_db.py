"""Seed PostgreSQL (same MNC demo as the old SQLite file)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.connection import SQLITE_PATH, sqlite_connect, try_postgres

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.postgres.sql"

MONTHS = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
AUDIT_MONTH = "2026-08"
SQLITE_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


class _SqliteCur:
    def __init__(self, conn):
        self.conn = conn
        self._last = None

    def execute(self, sql, params=None):
        self._last = self.conn.execute(sql.replace("%s", "?"), params or ())
        return self

    def fetchone(self):
        row = self._last.fetchone()
        if row is None:
            return None
        return dict(row)


def apply_postgres_schema_and_fill(conn) -> tuple[int, int]:
    """Wipe-and-seed money tables on an open Postgres connection. Caller may keep it open."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        _fill(cur)
        cur.execute("SELECT COUNT(*) AS n FROM cloud_line_items")
        n_cloud = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM saas_contracts")
        n_saas = cur.fetchone()["n"]
    conn.commit()
    return int(n_cloud), int(n_saas)


def main() -> None:
    try:
        conn = try_postgres()
        n_cloud, n_saas = apply_postgres_schema_and_fill(conn)
        conn.close()
        print(f"Seeded Postgres ({n_cloud} cloud rows, {n_saas} SaaS contracts)")
        return
    except Exception as exc:
        print(f"Postgres not ready ({type(exc).__name__}). Seeding SQLite for now.")

    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()
    conn = sqlite_connect()
    conn.executescript(SQLITE_SCHEMA.read_text(encoding="utf-8"))
    cur = _SqliteCur(conn)
    _fill(cur)
    cur.execute("SELECT COUNT(*) AS n FROM cloud_line_items")
    n_cloud = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM saas_contracts")
    n_saas = cur.fetchone()["n"]
    conn.commit()
    conn.close()
    print(f"Seeded SQLite {SQLITE_PATH} ({n_cloud} cloud rows, {n_saas} SaaS contracts)")


def _fill(cur) -> None:
    entities = [
        ("FinOptima US Inc", "US", "USD"),
        ("FinOptima Ireland Ltd", "IE", "EUR"),
        ("FinOptima India Pvt Ltd", "IN", "INR"),
    ]
    for name, country, currency in entities:
        cur.execute(
            "INSERT INTO legal_entities (name, country, currency) VALUES (%s, %s, %s)",
            (name, country, currency),
        )

    def entity_id(name: str) -> int:
        cur.execute("SELECT id FROM legal_entities WHERE name = %s", (name,))
        return cur.fetchone()["id"]

    departments = [
        ("FinOptima US Inc", "Engineering", "CC-US-ENG-100"),
        ("FinOptima US Inc", "Marketing", "CC-US-MKT-200"),
        ("FinOptima US Inc", "Sales", "CC-US-SLS-300"),
        ("FinOptima US Inc", "Operations", "CC-US-OPS-400"),
        ("FinOptima US Inc", "Finance", "CC-US-FIN-500"),
        ("FinOptima US Inc", "IT", "CC-US-IT-600"),
        ("FinOptima Ireland Ltd", "Engineering", "CC-IE-ENG-100"),
        ("FinOptima Ireland Ltd", "Operations", "CC-IE-OPS-400"),
        ("FinOptima India Pvt Ltd", "Engineering", "CC-IN-ENG-100"),
        ("FinOptima India Pvt Ltd", "Operations", "CC-IN-OPS-400"),
    ]
    for entity, name, cost_center in departments:
        cur.execute(
            """
            INSERT INTO departments (entity_id, name, cost_center)
            VALUES (%s, %s, %s)
            """,
            (entity_id(entity), name, cost_center),
        )

    def dept_id(entity: str, name: str) -> int:
        cur.execute(
            """
            SELECT d.id FROM departments d
            JOIN legal_entities e ON e.id = d.entity_id
            WHERE e.name = %s AND d.name = %s
            """,
            (entity, name),
        )
        return cur.fetchone()["id"]

    limits = {
        ("FinOptima US Inc", "Engineering"): 15000,
        ("FinOptima US Inc", "Marketing"): 5000,
        ("FinOptima US Inc", "Sales"): 4000,
        ("FinOptima US Inc", "Operations"): 8000,
        ("FinOptima US Inc", "Finance"): 2500,
        ("FinOptima US Inc", "IT"): 6000,
        ("FinOptima Ireland Ltd", "Engineering"): 9000,
        ("FinOptima Ireland Ltd", "Operations"): 5000,
        ("FinOptima India Pvt Ltd", "Engineering"): 4000,
        ("FinOptima India Pvt Ltd", "Operations"): 3000,
    }
    for (entity, name), limit_usd in limits.items():
        for month in MONTHS:
            cur.execute(
                """
                INSERT INTO monthly_budgets (department_id, year_month, limit_usd)
                VALUES (%s, %s, %s)
                """,
                (dept_id(entity, name), month, limit_usd),
            )

    baseline = [
        ("FinOptima US Inc", "Operations", "Datadog", "prod", "us-east-1", 2800),
        ("FinOptima US Inc", "Operations", "EKS", "prod", "us-east-1", 2100),
        ("FinOptima US Inc", "Operations", "Snowflake", "prod", "us-west-2", 1500),
        ("FinOptima US Inc", "Engineering", "EKS", "prod", "us-east-1", 7000),
        ("FinOptima US Inc", "Engineering", "Snowflake", "prod", "us-west-2", 3500),
        ("FinOptima US Inc", "Engineering", "GitHub Actions", "ci", "us-east-1", 800),
        ("FinOptima US Inc", "Marketing", "CloudFront", "prod", "global", 2800),
        ("FinOptima US Inc", "Sales", "Salesforce-infra", "prod", "us-east-1", 2200),
        ("FinOptima US Inc", "Finance", "S3", "prod", "us-east-1", 900),
        ("FinOptima US Inc", "IT", "Okta-infra", "prod", "us-east-1", 1800),
        ("FinOptima US Inc", "IT", "VPN", "prod", "us-east-1", 700),
        ("FinOptima Ireland Ltd", "Engineering", "EKS", "prod", "eu-west-1", 4200),
        ("FinOptima Ireland Ltd", "Engineering", "RDS", "prod", "eu-west-1", 2100),
        ("FinOptima Ireland Ltd", "Operations", "Datadog", "prod", "eu-west-1", 1900),
        ("FinOptima Ireland Ltd", "Operations", "CloudFront", "prod", "global", 800),
        ("FinOptima India Pvt Ltd", "Engineering", "EKS", "prod", "ap-south-1", 1800),
        ("FinOptima India Pvt Ltd", "Engineering", "S3", "prod", "ap-south-1", 400),
        ("FinOptima India Pvt Ltd", "Operations", "CloudWatch", "prod", "ap-south-1", 900),
        ("FinOptima India Pvt Ltd", "Operations", "S3", "prod", "ap-south-1", 350),
    ]
    for month in MONTHS:
        for entity, dept, service, env, region, amount in baseline:
            if (
                month == AUDIT_MONTH
                and entity == "FinOptima US Inc"
                and dept == "Operations"
                and service in ("Datadog", "EKS", "Snowflake")
            ):
                continue
            cur.execute(
                """
                INSERT INTO cloud_line_items
                    (department_id, year_month, service, environment, region, amount_usd)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (dept_id(entity, dept), month, service, env, region, amount),
            )

    for service, env, region, amount in (
        ("Datadog", "prod", "us-east-1", 9800),
        ("EKS", "prod", "us-east-1", 5400),
        ("Snowflake", "prod", "us-west-2", 4000),
    ):
        cur.execute(
            """
            INSERT INTO cloud_line_items
                (department_id, year_month, service, environment, region, amount_usd)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                dept_id("FinOptima US Inc", "Operations"),
                AUDIT_MONTH,
                service,
                env,
                region,
                amount,
            ),
        )

    saas_rows = [
        ("RedundantPM", "FinOptima US Inc", "Operations", "AcmePM", 25000, 45, "ops-lead@finoptima.example", 8.4, "2026-09"),
        ("LegacyTableau", "FinOptima US Inc", "Operations", "Tableau", 18000, 62, "bi@finoptima.example", 7.9, "2026-10"),
        ("AsanaDuplicate", "FinOptima US Inc", "Operations", "Asana", 14000, 38, "pmo@finoptima.example", 7.6, "2026-09"),
        ("Slack", "FinOptima US Inc", "Engineering", "Slack", 8000, 1, "eng-admin@finoptima.example", 1.2, "2027-01"),
        ("GitHub", "FinOptima US Inc", "Engineering", "GitHub", 12000, 0, "eng-admin@finoptima.example", 0.8, "2026-12"),
        ("Jira", "FinOptima US Inc", "Engineering", "Atlassian", 11000, 2, "eng-admin@finoptima.example", 1.4, "2027-02"),
        ("DatadogSaaS", "FinOptima US Inc", "Engineering", "Datadog", 22000, 3, "sre@finoptima.example", 2.0, "2026-11"),
        ("Figma", "FinOptima US Inc", "Marketing", "Figma", 3000, 5, "brand@finoptima.example", 2.1, "2026-11"),
        ("AdobeCC", "FinOptima US Inc", "Marketing", "Adobe", 9000, 8, "brand@finoptima.example", 2.4, "2027-01"),
        ("HubSpot", "FinOptima US Inc", "Sales", "HubSpot", 15000, 3, "sales-ops@finoptima.example", 1.5, "2027-03"),
        ("Salesforce", "FinOptima US Inc", "Sales", "Salesforce", 42000, 1, "sales-ops@finoptima.example", 1.1, "2026-12"),
        ("GongIdle", "FinOptima US Inc", "Sales", "Gong", 16000, 51, "sales-ops@finoptima.example", 8.1, "2026-10"),
        ("Workday", "FinOptima US Inc", "Finance", "Workday", 38000, 2, "fpna@finoptima.example", 1.0, "2027-04"),
        ("AnaplanShelf", "FinOptima US Inc", "Finance", "Anaplan", 21000, 71, "fpna@finoptima.example", 8.8, "2026-09"),
        ("Okta", "FinOptima US Inc", "IT", "Okta", 14000, 0, "it-sec@finoptima.example", 0.9, "2027-02"),
        ("ServiceNow", "FinOptima US Inc", "IT", "ServiceNow", 31000, 4, "it-sec@finoptima.example", 1.6, "2026-12"),
        ("Zoom", "FinOptima US Inc", "IT", "Zoom", 6000, 1, "it-sec@finoptima.example", 1.3, "2027-01"),
        ("MiroEU", "FinOptima Ireland Ltd", "Engineering", "Miro", 5000, 6, "dublin-eng@finoptima.example", 2.2, "2026-11"),
        ("GitLabEU", "FinOptima Ireland Ltd", "Engineering", "GitLab", 9000, 2, "dublin-eng@finoptima.example", 1.5, "2027-03"),
        ("ConfluenceEU", "FinOptima Ireland Ltd", "Engineering", "Atlassian", 4000, 9, "dublin-eng@finoptima.example", 2.8, "2026-10"),
        ("PagerDutyEU", "FinOptima Ireland Ltd", "Operations", "PagerDuty", 8000, 3, "dublin-ops@finoptima.example", 1.8, "2027-01"),
        ("OldStatuspage", "FinOptima Ireland Ltd", "Operations", "Atlassian", 4500, 88, "dublin-ops@finoptima.example", 7.2, "2026-09"),
        ("FreshdeskIN", "FinOptima India Pvt Ltd", "Operations", "Freshworks", 3500, 4, "blr-ops@finoptima.example", 2.0, "2027-02"),
        ("ZohoCRM", "FinOptima India Pvt Ltd", "Operations", "Zoho", 2800, 12, "blr-ops@finoptima.example", 3.1, "2026-11"),
        ("UnusedPostman", "FinOptima India Pvt Ltd", "Engineering", "Postman", 2400, 40, "blr-eng@finoptima.example", 6.4, "2026-10"),
        ("CursorSeats", "FinOptima India Pvt Ltd", "Engineering", "Anysphere", 3600, 2, "blr-eng@finoptima.example", 1.2, "2027-01"),
        ("NotionUS", "FinOptima US Inc", "Engineering", "Notion", 4800, 7, "eng-admin@finoptima.example", 2.3, "2026-12"),
        ("LinearApp", "FinOptima US Inc", "Engineering", "Linear", 3200, 3, "eng-admin@finoptima.example", 1.7, "2027-02"),
        ("LookerGhost", "FinOptima US Inc", "Finance", "Google", 19000, 55, "fpna@finoptima.example", 8.0, "2026-10"),
        ("Calendly", "FinOptima US Inc", "Sales", "Calendly", 2200, 6, "sales-ops@finoptima.example", 2.5, "2026-11"),
        ("DocuSign", "FinOptima US Inc", "Finance", "DocuSign", 7000, 2, "legal@finoptima.example", 1.4, "2027-03"),
        ("LastPassLegacy", "FinOptima US Inc", "IT", "LastPass", 1800, 94, "it-sec@finoptima.example", 7.5, "2026-09"),
    ]
    for name, entity, dept, vendor, arr, days, email, risk, renewal in saas_rows:
        cur.execute(
            """
            INSERT INTO saas_contracts
                (name, department_id, vendor, arr_usd, last_active_days_ago,
                 owner_email, risk_score, renewal_year_month)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, dept_id(entity, dept), vendor, arr, days, email, risk, renewal),
        )


if __name__ == "__main__":
    main()
