"""
setup_db.py — Khởi tạo database tnbike_db lần đầu

Bước 1: Tạo database (nếu chưa tồn tại)
Bước 2: Chạy schema SQL từ ../Database/01_create_tables.sql
Bước 3: Import dữ liệu lịch sử từ ../Database/02_import_data.sql

Chạy: python setup_db.py
"""

import psycopg2
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def setup_database():
    """Khởi tạo database từ đầu"""

    # ────────────────────────────────────────────────────────────────────────
    # Bước 0: Kết nối PostgreSQL server (không có database cụ thể)
    # ────────────────────────────────────────────────────────────────────────

    conn_server = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="123456",
        dbname="postgres"  # Kết nối tới postgres mặc định
    )
    conn_server.autocommit = True

    try:
        with conn_server.cursor() as cur:
            # Kiểm tra database tnbike_db tồn tại
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname='tnbike_db'"
            )
            if not cur.fetchone():
                print("✓ Tạo database tnbike_db...")
                cur.execute("CREATE DATABASE tnbike_db ENCODING 'UTF8'")
                print("  ✓ Tạo thành công!")
            else:
                print("✓ Database tnbike_db đã tồn tại")
    finally:
        conn_server.close()

    # ────────────────────────────────────────────────────────────────────────
    # Bước 1: Kết nối tới tnbike_db và chạy schema SQL
    # ────────────────────────────────────────────────────────────────────────

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="tnbike_db",
        user="postgres",
        password="123456"
    )
    conn.autocommit = True

    try:
        sql_folder = Path(__file__).parent.parent / "Database"

        # Chạy 01_create_tables.sql
        schema_file = sql_folder / "01_create_tables.sql"
        if schema_file.exists():
            print(f"\n✓ Chạy schema từ {schema_file.name}...")
            with open(schema_file, 'r', encoding='utf-8') as f:
                sql = f.read()

            with conn.cursor() as cur:
                cur.execute(sql)
            print("  ✓ Schema tạo thành công!")
        else:
            print(f"⚠ Không tìm thấy {schema_file}")

        # Chạy 02_import_data.sql
        data_file = sql_folder / "02_import_data.sql"
        if data_file.exists():
            print(f"\n✓ Import dữ liệu lịch sử từ {data_file.name}...")
            with open(data_file, 'r', encoding='utf-8') as f:
                sql = f.read()

            with conn.cursor() as cur:
                cur.execute(sql)
            print("  ✓ Dữ liệu lịch sử import thành công!")
        else:
            print(f"⚠ Không tìm thấy {data_file}")

        print("\n" + "="*70)
        print("✓ SETUP DATABASE THÀNH CÔNG!")
        print("="*70)
        print("Tiếp theo: python main.py")

    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
