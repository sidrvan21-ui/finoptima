from db.connection import fetchall, open_db


def test_open_db_has_cloud_rows():
    backend, conn = open_db()
    try:
        assert backend in ("postgres", "sqlite")
        rows = fetchall(conn, backend, "SELECT COUNT(*) AS n FROM cloud_line_items")
        assert int(rows[0]["n"]) > 0
    finally:
        conn.close()
