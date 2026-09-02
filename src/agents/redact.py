"""Mask owner emails before rows would go to an LLM. No GPT. Demo only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audit.engine import get_saas_flags


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def redact_saas_flags(flags: list[dict]) -> list[dict]:
    """Copy flags; replace owner_email with a masked value. Spend fields unchanged."""
    out: list[dict] = []
    for row in flags:
        copy = dict(row)
        copy["owner_email"] = mask_email(str(row.get("owner_email", "")))
        out.append(copy)
    return out


def main() -> None:
    raw = get_saas_flags()
    if not raw:
        print("No SaaS flags to redact. Rebuild DB: python src/db/build_db.py")
        return
    hidden = redact_saas_flags(raw)
    print("=== owner_email before / after mask ===")
    for before, after in zip(raw, hidden):
        print(f"{before['name']}: {before['owner_email']}  ->  {after['owner_email']}")


if __name__ == "__main__":
    main()
