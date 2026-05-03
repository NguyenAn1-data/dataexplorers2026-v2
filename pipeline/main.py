"""
main.py  —  Pipeline Xử lý Đơn hàng Tự động  (Hạng mục A)
===============================================================
Luồng xử lý:
  .eml → parse header + tách PDF → parse PDF → validate → DB insert
  → cuối cùng: populate fact_sales

Chạy:
  cd pipeline
  python main.py

Output:
  - Console: progress bar + summary
  - pipeline/logs/pipeline_YYYYMMDD_HHMMSS.json: chi tiết từng đơn
  - pipeline/logs/summary.json: số liệu tổng hợp cho Dashboard
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

# Đảm bảo import được các module trong cùng thư mục
sys.path.insert(0, str(Path(__file__).parent))

from config import DB_CONFIG, EML_FOLDER, LOG_FOLDER
from db_writer import (
    init_db,
    load_existing_so_numbers,
    load_processed_message_ids,
    load_valid_products,
    log_email_error,
    insert_order,
    lookup_customer,
    populate_fact_sales,
)
from parse_eml import parse_eml
from parse_pdf import parse_pdf
from validate import validate_order


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

os.makedirs(LOG_FOLDER, exist_ok=True)
run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_FOLDER}/pipeline_{run_ts}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _progress(current: int, total: int, prefix: str = "") -> None:
    pct = current / total * 100
    bar = "█" * int(pct // 2) + "░" * (50 - int(pct // 2))
    print(f"\r{prefix} [{bar}] {current}/{total} ({pct:.1f}%)", end="", flush=True)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> dict:
    start_time = time.time()
    log.info("=" * 60)
    log.info("TNBIKE PIPELINE — Hạng mục A bắt đầu")
    log.info(f"EML folder: {EML_FOLDER}")
    log.info("=" * 60)

    # ── Kết nối DB ───────────────────────────────────────────────────────────
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Kết nối PostgreSQL thành công")
    except Exception as e:
        log.error(f"Không kết nối được DB: {e}")
        sys.exit(1)

    # ── Khởi tạo DB ──────────────────────────────────────────────────────────
    init_db(conn)
    log.info("Bảng email_log đã sẵn sàng")

    # ── Load cache ───────────────────────────────────────────────────────────
    valid_products      = load_valid_products(conn)
    existing_so         = load_existing_so_numbers(conn)
    processed_msg_ids   = load_processed_message_ids(conn)
    log.info(f"Cache: {len(valid_products)} SKU | {len(existing_so)} đơn đã có | "
             f"{len(processed_msg_ids)} email đã xử lý")

    # ── Lấy danh sách file .eml ───────────────────────────────────────────────
    eml_files = sorted(Path(EML_FOLDER).glob("*.eml"))
    total = len(eml_files)
    log.info(f"Tổng số file .eml: {total}")

    # ── Counters ─────────────────────────────────────────────────────────────
    stats = {
        "total":        total,
        "success":      0,
        "duplicate":    0,
        "error_parse":  0,
        "error_validate": 0,
        "error_db":     0,
        "skipped_no_pdf": 0,
    }
    error_log = []      # chi tiết từng lỗi

    # ── Vòng lặp chính ───────────────────────────────────────────────────────
    for idx, eml_path in enumerate(eml_files, start=1):
        _progress(idx, total, "Xử lý")

        eml_data  = None
        so_number = ""

        try:
            # BƯỚC 1: Parse .eml
            eml_data = parse_eml(eml_path)

            if eml_data is None:
                log.warning(f"[SKIP] {eml_path.name}: Không có PDF đính kèm")
                stats["skipped_no_pdf"] += 1
                continue

            # Bỏ qua nếu message_id đã được xử lý trước đó
            if eml_data["message_id"] and eml_data["message_id"] in processed_msg_ids:
                stats["duplicate"] += 1
                continue

            # BƯỚC 2: Parse PDF
            pdf_data = parse_pdf(eml_data["pdf_bytes"])

            # Ưu tiên so_number từ PDF, fallback về email subject
            so_number = pdf_data.get("so_number") or eml_data.get("so_number_email", "")
            pdf_data["so_number"] = so_number

            # Ưu tiên tax_code từ PDF, fallback về body email
            if not pdf_data.get("tax_code") and eml_data.get("body_mst"):
                pdf_data["tax_code"] = eml_data["body_mst"]

        except Exception as e:
            msg = f"Lỗi parse file: {e}"
            log.error(f"[PARSE ERROR] {eml_path.name}: {msg}")
            stats["error_parse"] += 1
            error_log.append({"file": eml_path.name, "so_number": so_number,
                               "stage": "parse", "error": msg})
            if eml_data:
                log_email_error(conn, eml_data, so_number, msg)
            continue

        # BƯỚC 3: Validate
        errors = validate_order(eml_data, pdf_data, valid_products, existing_so)
        if errors:
            # Phân biệt duplicate vs lỗi khác
            is_dup = any("đã tồn tại" in e for e in errors)
            if is_dup:
                stats["duplicate"] += 1
            else:
                stats["error_validate"] += 1
                error_msg = "; ".join(errors)
                log.warning(f"[VALIDATE] {eml_path.name} ({so_number}): {error_msg}")
                error_log.append({"file": eml_path.name, "so_number": so_number,
                                   "stage": "validate", "error": error_msg})
                log_email_error(conn, eml_data, so_number, error_msg)
            continue

        # BƯỚC 4: Lookup customer
        tax_code = pdf_data.get("tax_code", "")
        customer_code = lookup_customer(conn, tax_code)

        if not customer_code:
            msg = f"Không tìm thấy đại lý với MST={tax_code}"
            log.warning(f"[NO CUSTOMER] {eml_path.name} ({so_number}): {msg}")
            stats["error_validate"] += 1
            error_log.append({"file": eml_path.name, "so_number": so_number,
                               "stage": "customer_lookup", "error": msg})
            log_email_error(conn, eml_data, so_number, msg)
            continue

        # BƯỚC 5: Ghi vào DB
        try:
            insert_order(conn, eml_data, pdf_data, customer_code)
            existing_so.add(so_number)          # cập nhật cache
            processed_msg_ids.add(eml_data["message_id"])
            stats["success"] += 1

        except Exception as e:
            conn.rollback()
            msg = f"Lỗi ghi DB: {e}"
            log.error(f"[DB ERROR] {eml_path.name} ({so_number}): {msg}")
            stats["error_db"] += 1
            error_log.append({"file": eml_path.name, "so_number": so_number,
                               "stage": "db_insert", "error": msg})
            log_email_error(conn, eml_data, so_number, msg)

    print()  # xuống dòng sau progress bar

    # ── Populate fact_sales ───────────────────────────────────────────────────
    log.info("Đang populate fact_sales cho T3/2026...")
    try:
        fact_count = populate_fact_sales(conn)
        log.info(f"fact_sales: đã insert {fact_count} dòng")
        stats["fact_rows_inserted"] = fact_count
    except Exception as e:
        log.error(f"Lỗi populate fact_sales: {e}")
        stats["fact_rows_inserted"] = 0

    # ── Tổng kết ─────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 2)
    stats["run_timestamp"] = run_ts

    error_rate = (stats["error_validate"] + stats["error_parse"] + stats["error_db"]) / total * 100
    pass_rate  = stats["success"] / total * 100

    log.info("=" * 60)
    log.info("KẾT QUẢ PIPELINE")
    log.info(f"  Tổng file             : {total}")
    log.info(f"  ✅ Thành công          : {stats['success']}")
    log.info(f"  ⚠️  Duplicate (skip)   : {stats['duplicate']}")
    log.info(f"  ❌ Lỗi parse          : {stats['error_parse']}")
    log.info(f"  ❌ Lỗi validate       : {stats['error_validate']}")
    log.info(f"  ❌ Lỗi DB             : {stats['error_db']}")
    log.info(f"  ⏭️  Bỏ qua (no PDF)    : {stats['skipped_no_pdf']}")
    log.info(f"  Tỷ lệ thành công      : {pass_rate:.1f}%")
    log.info(f"  Tỷ lệ lỗi            : {error_rate:.1f}%")
    log.info(f"  fact_sales rows       : {stats.get('fact_rows_inserted', 0)}")
    log.info(f"  Thời gian chạy        : {elapsed:.1f}s")
    log.info("=" * 60)

    # ── Lưu kết quả ra JSON (dùng cho Dashboard màn hình 6) ──────────────────
    summary_path = Path(LOG_FOLDER) / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    if error_log:
        error_path = Path(LOG_FOLDER) / f"errors_{run_ts}.json"
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(error_log, f, ensure_ascii=False, indent=2)
        log.info(f"Chi tiết lỗi: {error_path}")

    conn.close()
    return stats


# ---------------------------------------------------------------------------
# Verify sau khi chạy
# ---------------------------------------------------------------------------

def verify_results() -> None:
    """Kiểm tra nhanh kết quả trong DB sau khi pipeline hoàn thành."""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(DISTINCT so_number)   AS orders,
                SUM(total_quantity)         AS total_qty,
                SUM(total_amount)           AS total_revenue
            FROM tnbike.sales_order
            WHERE fiscal_year = 2026 AND fiscal_month = 3
        """)
        row = cur.fetchone()
        log.info(f"\n📊 VERIFY — T3/2026 trong sales_order:")
        log.info(f"   Số đơn hàng : {row[0]}")
        log.info(f"   Tổng SL     : {row[1]:,.0f}")
        log.info(f"   Doanh thu   : {row[2]:,.0f} VND")

        cur.execute("""
            SELECT COUNT(*) FROM tnbike.order_line ol
            JOIN tnbike.sales_order so ON so.order_id = ol.order_id
            WHERE so.fiscal_year = 2026 AND so.fiscal_month = 3
        """)
        log.info(f"   Dòng order_line: {cur.fetchone()[0]:,}")

        cur.execute("""
            SELECT COUNT(*) FROM tnbike.fact_sales
            WHERE fiscal_year = 2026 AND fiscal_month = 3
        """)
        log.info(f"   Dòng fact_sales : {cur.fetchone()[0]:,}")

        cur.execute("""
            SELECT processing_status, COUNT(*)
            FROM tnbike.email_log GROUP BY 1 ORDER BY 1
        """)
        log.info("   email_log breakdown:")
        for status, cnt in cur.fetchall():
            log.info(f"     {status}: {cnt}")

    conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    stats = run_pipeline()
    verify_results()
    sys.exit(0 if stats["success"] > 0 else 1)
