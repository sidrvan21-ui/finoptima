FinOptima is a FinOps copilot. Money lives in PostgreSQL. It finds cloud budget overruns and unused SaaS spend, matches them to written company policy, and pauses for a human to approve an executive memo before anything is sent. The database owns the numbers. The LLM does not invent money.

Start the database:

1. You already have **PostgreSQL 17** running on this PC. In pgAdmin, connect as `postgres` and run `src/db/setup_postgres.sql` (creates user/database `finoptima`).
2. Or, if you install Docker Desktop: `docker compose up -d` (same user/password).
3. Seed: `python src/db/build_db.py`
4. Flags: `python src/audit/engine.py`

`.env` must contain `DATABASE_URL=postgresql://finoptima:finoptima@127.0.0.1:5432/finoptima`
