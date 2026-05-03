"""
fix_missing_data.py
Xử lý 2 loại lỗi từ pipeline lần đầu:
  1. Khách hàng mới (MST chưa có trong DB) → tạo customer mới
  2. Sản phẩm mới (mã hàng chưa có trong DB) → thêm vào product table
Sau đó gọi lại pipeline cho các đơn lỗi.
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

# ─── Tải lỗi từ lần chạy trước ─────────────────────────────────────────────
logs = sorted(glob.glob("logs/errors_*.json"))
with open(logs[-1], encoding="utf-8") as f:
    errors = json.load(f)

mst_errors   = [e for e in errors if "MST=" in e.get("error", "")]
prod_errors  = [e for e in errors if "Mã hàng không tồn tại" in e.get("error", "")]

print(f"Lỗi missing customer: {len(mst_errors)} đơn ({len(set(e['error'].split('MST=')[1] for e in mst_errors))} MST unique)")
print(f"Lỗi missing product : {len(prod_errors)} đơn")

# ═══════════════════════════════════════════════════════════════════════════
# PHẦN 1: Đăng ký khách hàng mới từ email/PDF
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== FIX 1: Đăng ký khách hàng mới ===")

# Lấy max customer_code hiện tại để tạo KH mới tiếp theo
with conn.cursor() as cur:
    cur.execute("""
        SELECT MAX(CAST(REGEXP_REPLACE(customer_code, '[^0-9]', '', 'g') AS INTEGER))
        FROM tnbike.customer
    """)
    max_kh_num = cur.fetchone()[0] or 702

def get_province_id(conn, address: str) -> int | None:
    """Tra province_id từ địa chỉ dạng text."""
    if not address:
        return None
    with conn.cursor() as cur:
        cur.execute("SELECT province_id, province_name FROM tnbike.province")
        provinces = cur.fetchall()
    addr_upper = address.upper()
    for pid, pname in provinces:
        if pname.upper() in addr_upper or any(
            part.upper() in addr_upper
            for part in pname.replace("TP. ", "").replace("Tỉnh ", "").split()
            if len(part) > 3
        ):
            return pid
    return None

# Thu thập thông tin khách hàng mới từ PDF
new_customers = {}  # tax_code → {customer_name, address, province_id}

for err in mst_errors:
    fname = err["file"]
    mst   = err["error"].split("MST=")[1].strip()
    if mst in new_customers:
        continue

    eml_path = EML_FOLDER / fname
    if not eml_path.exists():
        continue

    try:
        eml = parse_eml(eml_path)
        if not eml:
            continue
        pdf = parse_pdf(eml["pdf_bytes"])
        if pdf.get("tax_code") == mst:
            address = ""
            # Lấy địa chỉ từ email body
            body_match = re.search(r"(?:Địa chỉ|Đia chi)\s*[:\|]\s*(.+)", eml.get("body_mst", "") + "\n")
            # Thử extract từ from_email domain để đoán tỉnh
            name = pdf.get("customer_name", "").strip()
            if name:
                new_customers[mst] = {
                    "customer_name": name,
                    "address": "",
                    "province_id": None,
                }
    except Exception as e:
        print(f"  Lỗi đọc {fname}: {e}")

print(f"Tìm được {len(new_customers)} khách hàng mới cần đăng ký")

# Insert khách hàng mới vào DB
inserted_customers = 0
with conn.cursor() as cur:
    for mst, info in new_customers.items():
        # Kiểm tra lại (phòng trường hợp đã được insert)
        cur.execute("SELECT customer_code FROM tnbike.customer WHERE tax_code = %s", (mst,))
        if cur.fetchone():
            continue

        max_kh_num += 1
        new_code = f"KH-{max_kh_num:05d}"
        cur.execute("""
            INSERT INTO tnbike.customer
                (customer_code, customer_name, tax_code, address, province_id, customer_tier)
            VALUES (%s, %s, %s, %s, %s, 'STANDARD')
            ON CONFLICT (customer_code) DO NOTHING
        """, (new_code, info["customer_name"], mst, info["address"], info["province_id"]))
        inserted_customers += 1

conn.commit()
print(f"Đã đăng ký {inserted_customers} khách hàng mới")

# ═══════════════════════════════════════════════════════════════════════════
# PHẦN 2: Đăng ký sản phẩm mới từ PDF
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== FIX 2: Đăng ký sản phẩm mới ===")

# Thu thập tất cả mã hàng bị lỗi và thông tin từ PDF
missing_products = {}  # product_code → {product_name, unit_price (từ PDF)}

for err in prod_errors:
    fname = err["file"]
    # Lấy danh sách mã hàng bị lỗi từ error message
    codes_in_err = re.findall(r"\d{10,16}", err.get("error", ""))

    eml_path = EML_FOLDER / fname
    if not eml_path.exists():
        continue

    try:
        eml = parse_eml(eml_path)
        if not eml:
            continue
        pdf = parse_pdf(eml["pdf_bytes"])
        for line in pdf.get("lines", []):
            code = line["product_code"]
            if code in codes_in_err and code not in missing_products:
                missing_products[code] = {
                    "product_code": code,
                    "unit_price":   line["unit_price"],
                }
    except Exception as e:
        print(f"  Lỗi đọc {fname}: {e}")

print(f"Tìm được {len(missing_products)} sản phẩm mới cần đăng ký")

inserted_products = 0
with conn.cursor() as cur:
    for code, info in missing_products.items():
        cur.execute("SELECT product_code FROM tnbike.product WHERE product_code = %s", (code,))
        if cur.fetchone():
            continue
        # Tạo tên tạm (không có thông tin đầy đủ từ PDF do encoding)
        product_name = f"Xe đạp Thống Nhất [{code}]"
        cur.execute("""
            INSERT INTO tnbike.product (product_code, product_name, unit, is_active)
            VALUES (%s, %s, 'Chiếc', TRUE)
            ON CONFLICT (product_code) DO NOTHING
        """, (code, product_name))
        inserted_products += 1

conn.commit()
print(f"Đã đăng ký {inserted_products} sản phẩm mới")

conn.close()
print("\n=== FIX HOÀN THÀNH — Chạy lại main.py để xử lý các đơn bị lỗi ===")
