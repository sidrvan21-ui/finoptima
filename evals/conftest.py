import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def pytest_sessionstart(session):
    from db.connection import SQLITE_PATH
    from db.build_db import main as seed_db

    if not SQLITE_PATH.exists():
        seed_db()
