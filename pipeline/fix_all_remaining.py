"""
Fix tổng quát: quét toàn bộ file lỗi còn lại,
tự động đăng ký khách hàng mới và sản phẩm mới vào DB.
"""
import sys, io, json, glob, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

import psycopg2
from pathlib import Path
from config import DB_CONFIG
from parse_eml import parse_eml
from parse_pdf import parse_pdf

EML_FOLDER = Path(r"d:\Data explore vòng 2\Emails & Files\tnbike_emails_mar2026")
conn = psycopg2.connect(**DB_CONFIG)

# Lấy max KH number hiện tại
with conn.cursor() as cur:
    cur.execute("""
        SELECT MAX(CAST(REGEXP_REPLACE(customer_code, '[^0-9]', '', 'g') AS INTEGER))
        FROM tnbike.customer
    """)
    max_kh = cur.fetchone()[0] or 795

# Load tất cả lỗi còn lại
all_error_files = sorted(glob.glob("logs/errors_*.json"))
all_errors = []
seen_files = set()
for ef in reversed(all_error_files):  # đọc từ mới nhất
    with open(ef, encoding="utf-8") as f:
        errs = json.load(f)
    for e in errs:
        if e["file"] not in seen_files:
            all_errors.append(e)
            seen_files.add(e["file"])

print(f"Tổng lỗi cần fix: {len(all_errors)}")

# Thu thập tất cả thông tin cần thiết từ file lỗi
missing_mst     = {}  # mst → {name}
missing_product = {}  # code → {name, price}

for err in all_errors:
    fname = err["file"]
    eml_path = EML_FOLDER / fname
    if not eml_path.exists():
        continue
    try:
        eml = parse_eml(eml_path)
        if not eml:
            continue
        pdf = parse_pdf(eml["pdf_bytes"])

        # Thu thập khách hàng mới
        mst = pdf.get("tax_code") or eml.get("body_mst", "")
        if mst and "MST=" in err.get("error", ""):
            err_mst = err["error"].split("MST=")[1].strip()
            if err_mst not in missing_mst:
                missing_mst[err_mst] = {"name": pdf.get("customer_name", f"KH MST {err_mst}")}

        # Thu thập sản phẩm mới
        if "không tồn tại trong DB" in err.get("error", ""):
            # Lấy danh sách mã bị lỗi từ error message
            # Cố gắng lấy tất cả codes trong error string
            codes_in_err = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]{7,19}", err.get("error", ""))
            for line in pdf.get("lines", []):
                code = line["product_code"]
                if code in codes_in_err and code not in missing_product:
                    missing_product[code] = {
                        "name": f"Xe đạp Thống Nhất [{code}]",
                        "price": line["unit_price"],
                    }
    except Exception as e:
        pass  # bỏ qua file bị lỗi parse

print(f"Khách hàng mới cần thêm: {len(missing_mst)}")
print(f"Sản phẩm mới cần thêm  : {len(missing_product)}")

# Insert khách hàng
added_kh = 0
with conn.cursor() as cur:
    for mst, info in missing_mst.items():
        cur.execute("SELECT 1 FROM tnbike.customer WHERE tax_code = %s", (mst,))
        if not cur.fetchone():
            max_kh += 1
            code = f"KH-{max_kh:05d}"
            cur.execute("""
                INSERT INTO tnbike.customer (customer_code, customer_name, tax_code, customer_tier)
                VALUES (%s, %s, %s, 'STANDARD') ON CONFLICT DO NOTHING
            """, (code, info["name"], mst))
            added_kh += 1
            print(f"  + KH {code}: {info['name'][:40]} (MST={mst})")
conn.commit()

# Insert sản phẩm
added_prod = 0
with conn.cursor() as cur:
    for code, info in missing_product.items():
        cur.execute("SELECT 1 FROM tnbike.product WHERE product_code = %s", (code,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO tnbike.product (product_code, product_name, unit, is_active)
                VALUES (%s, %s, 'Chiếc', TRUE) ON CONFLICT DO NOTHING
            """, (code, info["name"]))
            added_prod += 1
            print(f"  + SP {code}: {info['name'][:40]}")
conn.commit()
conn.close()

print(f"\nĐã thêm: {added_kh} khách hàng, {added_prod} sản phẩm")
print("→ Chạy main.py để xử lý nốt các đơn bị lỗi")
