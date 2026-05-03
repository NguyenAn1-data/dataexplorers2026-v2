"""Fix cuối: thêm 2 SP đặc biệt và 2 KH còn thiếu."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)

# Lấy max KH hiện tại
with conn.cursor() as cur:
    cur.execute("""
        SELECT MAX(CAST(REGEXP_REPLACE(customer_code, '[^0-9]', '', 'g') AS INTEGER))
        FROM tnbike.customer
    """)
    max_kh = cur.fetchone()[0] or 794

# 1. Thêm sản phẩm đặc biệt
special_products = [
    ("TP0099.0000570", "Xe đạp Thống Nhất Unite 26", "Chiếc"),
    ("156.01.12.0003", "Xe đạp Thống Nhất Unite 20", "Chiếc"),
]
with conn.cursor() as cur:
    for code, name, unit in special_products:
        cur.execute("SELECT 1 FROM tnbike.product WHERE product_code = %s", (code,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO tnbike.product (product_code, product_name, unit) VALUES (%s, %s, %s)",
                (code, name, unit)
            )
            print(f"Added product: {code}")
        else:
            print(f"Product exists: {code}")

# 2. Thêm KH còn thiếu (MST 170203772 và 295320846)
missing_customers = [
    ("170203772", "KHÁCH HÀNG MỚI 170203772"),
    ("295320846", "CỬA HÀNG XE ĐẠP XUÂN MAI"),
]
with conn.cursor() as cur:
    for mst, name in missing_customers:
        cur.execute("SELECT 1 FROM tnbike.customer WHERE tax_code = %s", (mst,))
        if not cur.fetchone():
            max_kh += 1
            code = f"KH-{max_kh:05d}"
            cur.execute("""
                INSERT INTO tnbike.customer (customer_code, customer_name, tax_code, customer_tier)
                VALUES (%s, %s, %s, 'STANDARD')
            """, (code, name, mst))
            print(f"Added customer: {code} MST={mst}")
        else:
            print(f"Customer exists: MST={mst}")

conn.commit()
conn.close()
print("Done.")
