import sys, io, psycopg2
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
conn = psycopg2.connect(host="localhost", dbname="tnbike_db", user="postgres", password="123456")
cur = conn.cursor()
for schema in ["tnbike", "tnbike_forecast"]:
    cur.execute("""
        SELECT table_name, table_type FROM information_schema.tables
        WHERE table_schema=%s ORDER BY table_type, table_name
    """, (schema,))
    rows = cur.fetchall()
    print(f"\n=== schema {schema} ({len(rows)} objects) ===")
    for r in rows:
        print(f"   {r[1]:12s}  {r[0]}")
cur.close(); conn.close()
