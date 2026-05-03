"""Phân tích lỗi pipeline và tìm cách fix missing customer."""
import sys, io, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

import psycopg2
from config import DB_CONFIG

logs = sorted(glob.glob("logs/errors_*.json"))
with open(logs[-1], encoding="utf-8") as f:
    errors = json.load(f)

# Lỗi không phải no-customer
other_errors = [e for e in errors if "MST=" not in e.get("error", "")]
print(f"Lỗi không phải no-customer: {len(other_errors)}")
for e in other_errors[:5]:
    print(f"  {e['file']}: stage={e['stage']} | {e['error'][:100]}")

print()
conn = psycopg2.connect(**DB_CONFIG)
with conn.cursor() as cur:
    # Kiểm tra format tax_code trong DB
    cur.execute("SELECT tax_code, customer_code, customer_name FROM tnbike.customer WHERE tax_code IS NOT NULL LIMIT 5")
    print("Sample tax_codes in DB:")
    for r in cur.fetchall():
        print(f"  tax_code='{r[0]}' (len={len(r[0])}) → {r[1]}: {r[2][:40]}")

    # Đếm bao nhiêu customer KHÔNG có tax_code
    cur.execute("SELECT COUNT(*) FROM tnbike.customer WHERE tax_code IS NULL OR tax_code = ''")
    print(f"\nCustomer không có tax_code: {cur.fetchone()[0]}")

    # Lấy danh sách MST bị lỗi và thử match theo customer_name
    mst_errors = [e for e in errors if "MST=" in e.get("error", "")]
    missing_mst = list(set(e["error"].split("MST=")[1].strip() for e in mst_errors))
    print(f"\nUnique MST không tìm thấy: {len(missing_mst)}")
    print("Thử match bằng customer_name từ email body (sample 3):")

    for mst in missing_mst[:3]:
        # Lấy tên đại lý từ file lỗi tương ứng
        matching_errs = [e for e in mst_errors if mst in e.get("error", "")]
        fname = matching_errs[0]["file"] if matching_errs else ""
        print(f"  MST {mst} → file: {fname}")

conn.close()
