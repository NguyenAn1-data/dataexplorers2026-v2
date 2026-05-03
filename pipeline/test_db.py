"""Test kết nối DB, lookup customer, và validate."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

import psycopg2
from config import DB_CONFIG
from db_writer import (
    init_db, load_valid_products, load_existing_so_numbers,
    lookup_customer
)
from parse_eml import parse_eml
from parse_pdf import parse_pdf
from validate import validate_order
from pathlib import Path

EML_FOLDER = Path(r"d:\Data explore vòng 2\Emails & Files\tnbike_emails_mar2026")

print("=== TEST DB CONNECTION ===")
conn = psycopg2.connect(**DB_CONFIG)
print("Kết nối OK")

print("\n=== INIT DB (tạo email_log) ===")
init_db(conn)
print("email_log ready")

print("\n=== LOAD CACHE ===")
valid_products = load_valid_products(conn)
existing_so    = load_existing_so_numbers(conn)
print(f"SKU hợp lệ      : {len(valid_products)}")
print(f"Đơn đã có       : {len(existing_so)}")

print("\n=== TEST CUSTOMER LOOKUP ===")
test_mst_list = ["167397253", "114724820", "111558627", "999999999"]
for mst in test_mst_list:
    code = lookup_customer(conn, mst)
    print(f"  MST {mst} → customer_code: {code}")

print("\n=== TEST VALIDATE trên 3 file ===")
for fname in ["BH26_0935.eml", "BH26_0939.eml", "BH26_1010.eml"]:
    eml  = parse_eml(EML_FOLDER / fname)
    pdf  = parse_pdf(eml["pdf_bytes"])
    so   = pdf.get("so_number") or eml.get("so_number_email", "")
    pdf["so_number"] = so

    errors = validate_order(eml, pdf, valid_products, existing_so)
    status = "PASS" if not errors else f"FAIL: {errors}"
    print(f"  {fname}: {status}")

conn.close()
print("\nDone.")
