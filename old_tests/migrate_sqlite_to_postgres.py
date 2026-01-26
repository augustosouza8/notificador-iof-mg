
import json
import sqlite3
import sys
import psycopg

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else "backup-local.db"
PG_DSN = sys.argv[2] if len(sys.argv) > 2 else None

if not PG_DSN:
    raise SystemExit("Uso: python migrate_sqlite_to_postgres.py <sqlite_db_path> <postgres_dsn>")

def to_bool(v):
    # SQLite costuma armazenar boolean como 0/1; mas aceitamos True/False/None também
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    try:
        return bool(int(v))
    except Exception:
        return bool(v)

con = sqlite3.connect(SQLITE_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

configs = cur.execute("SELECT * FROM search_configs").fetchall()
terms = cur.execute("SELECT * FROM search_terms").fetchall()

print(f"SQLite: {len(configs)} configs, {len(terms)} termos")

with psycopg.connect(PG_DSN) as pg:
    with pg.cursor() as c:

        # Inserir configs preservando IDs
        for row in configs:
            mail_to = row["mail_to"] if row["mail_to"] is not None else json.dumps([])

            c.execute(
                """
                INSERT INTO search_configs
                (id, label, description, attach_csv, mail_to, mail_subject, teams_webhook, active, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    row["id"],
                    row["label"],
                    row["description"],
                    to_bool(row["attach_csv"]),     # <-- FIX AQUI
                    mail_to,
                    row["mail_subject"],
                    row["teams_webhook"],
                    to_bool(row["active"]),         # <-- FIX AQUI
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        # Inserir termos preservando IDs
        for row in terms:
            c.execute(
                """
                INSERT INTO search_terms
                (id, term, exact, search_config_id)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    row["id"],
                    row["term"],
                    to_bool(row["exact"]),          # <-- FIX AQUI
                    row["search_config_id"],
                ),
            )

        # Ajustar sequences para futuros inserts
        c.execute("SELECT setval(pg_get_serial_sequence('search_configs','id'), COALESCE((SELECT MAX(id) FROM search_configs), 1), true);")
        c.execute("SELECT setval(pg_get_serial_sequence('search_terms','id'), COALESCE((SELECT MAX(id) FROM search_terms), 1), true);")

    pg.commit()

print("Migração concluída com sucesso.")