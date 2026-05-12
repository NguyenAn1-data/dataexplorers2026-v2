"""
main.py — Pipeline xử lý 1.132 email + PDF đơn hàng T3/2026

Quy trình:
  1. Parse từng file .eml → extract email metadata + PDF bytes
  2. Parse PDF bytes → extract số đơn, ngày, MST, tên KH, sản phẩm
  3. Validate dữ liệu (mã hàng, số lượng, thành tiền)
  4. Lookup customer từ MST
  5. Insert sales_order + order_line + email_log vào PostgreSQL
  6. Populate fact_sales sau xử lý toàn bộ
  7. Chạy clean_all.py để cleaning dữ liệu

Chạy: python main.py
"""

import sys
import psycopg2
from pathlib import Path
from tqdm import tqdm

# Import các module pipeline
try:
    from parse_eml import parse_eml
    from parse_pdf import parse_pdf
    from db_writer import (
        init_db, load_valid_products, load_existing_so_numbers,
        load_processed_message_ids, lookup_customer, insert_order,
        log_email_error, populate_fact_sales
    )
    from clean_all import main as clean_all_main
except ImportError as e:
    print(f"✗ Lỗi import: {e}")
    sys.exit(1)

# Cấu hình encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ═════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════════════════════

try:
    from config import DB_CONFIG, EML_FOLDER, LIMIT_FILES, DEBUG
except ImportError:
    print("✗ Không tìm thấy config.py")
    print("   Hãy copy config.example.py → config.py và cấu hình lại!")
    sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═════════════════════════════════════════════════════════════════════════════

def validate_product_lines(conn, lines: list) -> tuple[bool, str]:
    """Kiểm tra toàn bộ product_code trong order tồn tại trong DB."""
    valid_products = load_valid_products(conn)
    for line in lines:
        code = line.get("product_code", "").strip()
        if not code:
            return False, "Sản phẩm có mã hàng trống"
        if code not in valid_products:
            return False, f"Mã hàng {code} không tồn tại"
    return True, ""


def validate_order_data(pdf_data: dict) -> tuple[bool, str]:
    """Kiểm tra dữ liệu PDF được trích đúng."""
    if not pdf_data.get("so_number"):
        return False, "Không trích được số đơn"
    if not pdf_data.get("order_date"):
        return False, "Không trích được ngày đơn"
    if not pdf_data.get("tax_code"):
        return False, "Không trích được MST"
    if not pdf_data.get("customer_name"):
        return False, "Không trích được tên KH"
    if not pdf_data.get("lines"):
        return False, "Không tìm sản phẩm trong PDF"
    return True, ""


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def run_pipeline():
    """Chạy toàn bộ pipeline xử lý email + PDF."""

    # ─────────────────────────────────────────────────────────────────────────
    # Kết nối DB
    # ─────────────────────────────────────────────────────────────────────────

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"✗ Lỗi kết nối PostgreSQL: {e}")
        print(f"  Config: {DB_CONFIG['host']}:{DB_CONFIG['port']} / {DB_CONFIG['dbname']}")
        print("  Hãy cấu hình lại config.py!")
        sys.exit(1)

    print("✓ Kết nối PostgreSQL thành công\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Khởi tạo + Load cache
    # ─────────────────────────────────────────────────────────────────────────

    init_db(conn)
    print("✓ Bảng email_log sẵn sàng")

    valid_products = load_valid_products(conn)
    existing_so = load_existing_so_numbers(conn)
    processed_msg_ids = load_processed_message_ids(conn)

    print(f"✓ Cache: {len(valid_products)} mã hàng, {len(existing_so)} SO tồn tại")
    print(f"✓ Đã xử lý thành công: {len(processed_msg_ids)} email\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Quét file .eml
    # ─────────────────────────────────────────────────────────────────────────

    eml_folder = Path(EML_FOLDER)
    if not eml_folder.exists():
        print(f"✗ Thư mục email không tồn tại: {eml_folder}")
        print("  Cấu hình EML_FOLDER trong config.py")
        sys.exit(1)

    eml_files = sorted(eml_folder.glob("*.eml"))
    if LIMIT_FILES > 0:
        eml_files = eml_files[:LIMIT_FILES]

    print(f"✓ Tìm thấy {len(eml_files)} file .eml\n")

    if not eml_files:
        print("⚠ Không tìm thấy file .eml nào!")
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Xử lý từng email
    # ─────────────────────────────────────────────────────────────────────────

    stats = {
        "success": 0,
        "duplicate": 0,
        "error": 0,
        "lines_inserted": 0,
    }

    with tqdm(total=len(eml_files), desc="Xử lý email", unit="file") as pbar:
        for eml_path in eml_files:
            pbar.update(1)

            # 1. Parse EML
            try:
                eml_data = parse_eml(eml_path)
                if eml_data is None:
                    stats["error"] += 1
                    error_msg = "Không tìm PDF đính kèm"
                    log_email_error(conn, {"message_id": eml_path.name}, "", error_msg)
                    continue

                msg_id = eml_data.get("message_id", "")

                # Kiểm tra đã xử lý rồi
                if msg_id in processed_msg_ids:
                    stats["duplicate"] += 1
                    continue

            except Exception as e:
                stats["error"] += 1
                if DEBUG:
                    print(f"  ✗ Parse EML {eml_path.name}: {e}")
                continue

            # 2. Parse PDF
            try:
                pdf_data = parse_pdf(eml_data["pdf_bytes"])

                # Validate PDF data
                valid, err_msg = validate_order_data(pdf_data)
                if not valid:
                    stats["error"] += 1
                    log_email_error(conn, eml_data, "", f"PDF invalid: {err_msg}")
                    if DEBUG:
                        print(f"  ✗ PDF {eml_data['attachment_name']}: {err_msg}")
                    continue

            except Exception as e:
                stats["error"] += 1
                log_email_error(conn, eml_data, "", f"Parse PDF error: {str(e)[:500]}")
                if DEBUG:
                    print(f"  ✗ Parse PDF {eml_data['attachment_name']}: {e}")
                continue

            so_number = pdf_data["so_number"]

            # 3. Kiểm tra duplicate SO
            if so_number in existing_so:
                stats["duplicate"] += 1
                log_email_error(conn, eml_data, so_number, "SO đã tồn tại")
                continue

            # 4. Validate products
            valid, err_msg = validate_product_lines(conn, pdf_data["lines"])
            if not valid:
                stats["error"] += 1
                log_email_error(conn, eml_data, so_number, f"Product invalid: {err_msg}")
                if DEBUG:
                    print(f"  ✗ SO {so_number}: {err_msg}")
                continue

            # 5. Lookup customer
            tax_code = pdf_data.get("tax_code", "")
            customer_code = lookup_customer(conn, tax_code)
            if not customer_code:
                stats["error"] += 1
                log_email_error(conn, eml_data, so_number, f"MST {tax_code} không tìm KH")
                if DEBUG:
                    print(f"  ✗ SO {so_number}: MST {tax_code} không tìm KH")
                continue

            # 6. Insert vào DB
            try:
                order_id = insert_order(conn, eml_data, pdf_data, customer_code)
                stats["success"] += 1
                stats["lines_inserted"] += len(pdf_data["lines"])
                existing_so.add(so_number)
                processed_msg_ids.add(msg_id)
            except psycopg2.Error as e:
                stats["error"] += 1
                log_email_error(conn, eml_data, so_number, f"DB insert error: {str(e)[:500]}")
                if DEBUG:
                    print(f"  ✗ SO {so_number}: {e}")
                continue

    # ─────────────────────────────────────────────────────────────────────────
    # Populate fact_sales
    # ─────────────────────────────────────────────────────────────────────────

    print("\n✓ Xử lý email xong, populate fact_sales...")
    try:
        fact_sales_count = populate_fact_sales(conn)
        print(f"✓ fact_sales: {fact_sales_count} dòng inserted")
    except psycopg2.Error as e:
        print(f"⚠ Lỗi populate fact_sales: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Báo cáo
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "="*70)
    print("KẾT QUẢ PIPELINE PHASE A")
    print("="*70)
    print(f"SUCCESS:       {stats['success']:6d} đơn hàng")
    print(f"DUPLICATE:     {stats['duplicate']:6d} đơn (đã xử lý)")
    print(f"ERROR:         {stats['error']:6d} đơn (lỗi)")
    print(f"LINES:         {stats['lines_inserted']:6d} dòng sản phẩm")
    print("="*70)

    # Kiểm tra số liệu
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tnbike.sales_order WHERE fiscal_year=2026 AND fiscal_month=3")
        so_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tnbike.order_line WHERE order_id IN (SELECT order_id FROM tnbike.sales_order WHERE fiscal_year=2026 AND fiscal_month=3)")
        ol_count = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(line_total), 0) FROM tnbike.order_line WHERE order_id IN (SELECT order_id FROM tnbike.sales_order WHERE fiscal_year=2026 AND fiscal_month=3)")
        total_amt = cur.fetchone()[0]

    print(f"Database stats (T3/2026):")
    print(f"  sales_order: {so_count} rows")
    print(f"  order_line:  {ol_count} rows")
    print(f"  Doanh thu:   {total_amt:,.0f} VND")
    print("="*70)

    conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Chạy cleaning data (optional)
    # ─────────────────────────────────────────────────────────────────────────

    if stats["success"] > 0:
        print("\n✓ Bước kế tiếp: Cleaning dữ liệu...")
        try:
            clean_all_main()
        except Exception as e:
            print(f"⚠ Lỗi clean_all.py: {e}")
            print("  Bạn có thể chạy thủ công sau: python clean_all.py")


if __name__ == "__main__":
    run_pipeline()
