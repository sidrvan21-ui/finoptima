from __future__ import annotations

import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.connection import fetchall, open_db

MONTH = "2026-08"


def get_cloud_flags(year_month: str = MONTH) -> List[dict]:
    """Flag overspend in SQL (HAVING). Postgres if up, else SQLite."""
    backend, conn = open_db()
    rows = fetchall(
        conn,
        backend,
        """
        SELECT e.name AS entity,
               d.name AS department,
               d.cost_center,
               b.limit_usd,
               SUM(c.amount_usd) AS actual
        FROM cloud_line_items c
        JOIN departments d ON d.id = c.department_id
        JOIN legal_entities e ON e.id = d.entity_id
        JOIN monthly_budgets b
          ON b.department_id = d.id AND b.year_month = c.year_month
        WHERE c.year_month = %s
        GROUP BY e.name, d.name, d.cost_center, b.limit_usd
        HAVING (SUM(c.amount_usd) - b.limit_usd) / NULLIF(b.limit_usd, 0) > 0.15
            OR (SUM(c.amount_usd) - b.limit_usd) > 5000
        """,
        (year_month,),
    )
    conn.close()

    flags: List[dict] = []
    for row in rows:
        actual = float(row["actual"])
        limit = float(row["limit_usd"])
        over_usd = actual - limit
        over_pct = over_usd / limit
        flag_11 = over_pct > 0.15
        flag_12 = over_usd > 5000
        flags.append(
            {
                "entity": row["entity"],
                "department": row["department"],
                "cost_center": row["cost_center"],
                "actual": actual,
                "limit": limit,
                "over_usd": over_usd,
                "over_pct": over_pct,
                "rules": [r for r, on in (("1.1", flag_11), ("1.2", flag_12)) if on],
            }
        )
    return flags


def get_saas_flags() -> List[dict]:
    """Idle SaaS flags. Includes owner_email for redact."""
    backend, conn = open_db()
    rows = fetchall(
        conn,
        backend,
        """
        SELECT e.name AS entity,
               d.name AS department,
               s.name,
               s.arr_usd,
               s.last_active_days_ago,
               s.risk_score,
               s.owner_email
        FROM saas_contracts s
        JOIN departments d ON d.id = s.department_id
        JOIN legal_entities e ON e.id = d.entity_id
        WHERE s.last_active_days_ago >= 30
        ORDER BY s.arr_usd DESC
        """,
    )
    conn.close()

    flags: List[dict] = []
    for row in rows:
        arr = float(row["arr_usd"])
        p1 = arr > 10000
        flags.append(
            {
                "entity": row["entity"],
                "department": row["department"],
                "name": row["name"],
                "arr_usd": arr,
                "last_active_days_ago": row["last_active_days_ago"],
                "risk_score": float(row["risk_score"]),
                "owner_email": row["owner_email"],
                "rules": ["2.1"] + (["2.2"] if p1 else []),
            }
        )
    return flags


def main() -> None:
    print("=== Cloud flags ===")
    for row in get_cloud_flags():
        print(
            f"FLAG {row['entity']} / {row['department']} "
            f"({row['cost_center']}): actual={row['actual']} limit={row['limit']} "
            f"over_usd={row['over_usd']} over_pct={row['over_pct']:.0%} "
            f"rules={row['rules']}"
        )

    print("=== SaaS flags ===")
    for row in get_saas_flags():
        print(
            f"FLAG {row['entity']} / {row['name']}: arr={row['arr_usd']} "
            f"idle_days={row['last_active_days_ago']} "
            f"risk={row['risk_score']} "
            f"rules={row['rules']}"
        )


if __name__ == "__main__":
    main()
