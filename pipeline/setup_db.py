"""
setup_db.py
Tạo database tnbike_db và chạy các file SQL setup.
Chạy 1 lần duy nhất trước khi chạy main.py.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

PG_ADMIN = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",      # kết nối vào postgres DB để tạo tnbike_db
    "user": "postgres",
    "password": "123456",
}

DB_NAME   = "tnbike_db"
SQL_FOLDER = Path(r"d:\Data explore vòng 2\Database")

def create_database():
    conn = psycopg2.connect(**PG_ADMIN)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if cur.fetchone():
            print(f"Database '{DB_NAME}' đã tồn tại, bỏ qua tạo mới.")
        else:
            cur.execute(f"CREATE DATABASE {DB_NAME} ENCODING 'UTF8'")
            print(f"Database '{DB_NAME}' đã được tạo.")
    conn.close()

def run_sql_file(conn, path: Path):
    print(f"Đang chạy: {path.name} ...")
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  → Hoàn thành: {path.name}")

if __name__ == "__main__":
    print("=== SETUP TNBIKE_DB ===\n")

    # 1. Tạo database
    create_database()

    # 2. Kết nối vào tnbike_db
    conn = psycopg2.connect(
        host="localhost", port=5432,
        dbname=DB_NAME, user="postgres", password="123456"
    )

    # 3. Chạy DDL
    ddl_path = SQL_FOLDER / "01_create_tables.sql"
    if ddl_path.exists():
        run_sql_file(conn, ddl_path)
    else:
        print(f"KHÔNG TÌM THẤY: {ddl_path}")
        sys.exit(1)

    # 4. Import dữ liệu lịch sử
    data_path = SQL_FOLDER / "02_import_data.sql"
    if data_path.exists():
        print(f"Đang chạy: {data_path.name} (có thể mất 1-2 phút)...")
        sql = data_path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"  → Hoàn thành: {data_path.name}")
    else:
        print(f"KHÔNG TÌM THẤY: {data_path}")
        sys.exit(1)

    # 5. Verify
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tnbike.sales_order")
        print(f"\nVerify sales_order: {cur.fetchone()[0]:,} dòng")
        cur.execute("SELECT COUNT(*) FROM tnbike.customer")
        print(f"Verify customer   : {cur.fetchone()[0]:,} đại lý")
        cur.execute("SELECT COUNT(*) FROM tnbike.product")
        print(f"Verify product    : {cur.fetchone()[0]:,} SKU")
        cur.execute("SELECT COUNT(*) FROM tnbike.fact_sales")
        print(f"Verify fact_sales : {cur.fetchone()[0]:,} dòng")

    conn.close()
    print("\n=== SETUP HOÀN THÀNH — Sẵn sàng chạy main.py ===")
