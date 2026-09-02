-- Run as a Postgres superuser (pgAdmin or: psql -U postgres).
-- Then: python src/db/build_db.py

CREATE USER finoptima WITH PASSWORD 'finoptima';
CREATE DATABASE finoptima OWNER finoptima;
GRANT ALL PRIVILEGES ON DATABASE finoptima TO finoptima;

\connect finoptima
GRANT ALL ON SCHEMA public TO finoptima;
ALTER SCHEMA public OWNER TO finoptima;
