"""
db_writer.py
Tất cả thao tác với PostgreSQL:
  - init_db()             : tạo bảng email_log nếu chưa có
  - load_valid_products() : cache mã hàng hợp lệ
  - load_existing_so()    : cache số đơn hàng đã có
  - lookup_customer()     : tra customer_code từ MST
  - insert_order()        : ghi email_log + sales_order + order_line (1 transaction)
  - populate_fact_sales() : INSERT hàng loạt vào fact_sales sau khi xử lý xong
  - log_email_error()     : ghi email_log với trạng thái lỗi
"""

import psycopg2
from psycopg2.extras import execute_batch


# ---------------------------------------------------------------------------
# Khởi tạo
# ---------------------------------------------------------------------------

CREATE_EMAIL_LOG = """
CREATE TABLE IF NOT EXISTS tnbike.email_log (
    log_id              SERIAL          PRIMARY KEY,
    message_id          VARCHAR(300)    UNIQUE,
    from_address        TEXT,
    received_at         TIMESTAMPTZ,
    attachment_name     VARCHAR(300),
    so_number           VARCHAR(20),
    processing_status   VARCHAR(20)     DEFAULT 'PENDING',
    error_detail        TEXT,
    processed_at        TIMESTAMPTZ     DEFAULT NOW()
);
COMMENT ON TABLE tnbike.email_log IS
  'Log xử lý email đặt hàng T3/2026 — Hạng mục A pipeline';
"""


def init_db(conn) -> None:
    """Tạo bảng email_log nếu chưa tồn tại."""
    with conn.cursor() as cur:
        cur.execute(CREATE_EMAIL_LOG)
    conn.commit()


# ---------------------------------------------------------------------------
# Cache dữ liệu tham chiếu
# ---------------------------------------------------------------------------

def load_valid_products(conn) -> set:
    """Trả về set tất cả product_code hợp lệ."""
    with conn.cursor() as cur:
        cur.execute("SELECT product_code FROM tnbike.product")
        return {row[0] for row in cur.fetchall()}


def load_existing_so_numbers(conn) -> set:
    """Trả về set so_number đã có trong sales_order (tránh duplicate)."""
    with conn.cursor() as cur:
        cur.execute("SELECT so_number FROM tnbike.sales_order")
        return {row[0] for row in cur.fetchall()}


def load_processed_message_ids(conn) -> set:
    """Trả về set message_id đã xử lý THÀNH CÔNG — ERROR sẽ được retry."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT message_id FROM tnbike.email_log "
            "WHERE message_id IS NOT NULL AND processing_status = 'SUCCESS'"
        )
        return {row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Lookup customer
# ---------------------------------------------------------------------------

def lookup_customer(conn, tax_code: str) -> str | None:
    """
    Tra customer_code từ MST (tax_code).
    Thử exact match trước, sau đó thử strip leading zeros.
    """
    if not tax_code:
        return None
    with conn.cursor() as cur:
        # Exact match
        cur.execute(
            "SELECT customer_code FROM tnbike.customer WHERE tax_code = %s LIMIT 1",
            (tax_code,)
        )
        row = cur.fetchone()
        if row:
            return row[0]

        # Thử khớp bằng cách bỏ leading zeros
        tax_stripped = tax_code.lstrip("0")
        if tax_stripped != tax_code:
            cur.execute(
                "SELECT customer_code FROM tnbike.customer "
                "WHERE LTRIM(tax_code, '0') = %s LIMIT 1",
                (tax_stripped,)
            )
            row = cur.fetchone()
            if row:
                return row[0]

    return None


# ---------------------------------------------------------------------------
# Insert order (email_log + sales_order + order_line) — 1 transaction
# ---------------------------------------------------------------------------

def insert_order(conn, eml_data: dict, pdf_data: dict, customer_code: str) -> int:
    """
    Ghi 1 đơn hàng vào DB trong 1 transaction.
    Trả về order_id vừa tạo.
    """
    so_number   = pdf_data["so_number"]
    order_date  = pdf_data["order_date"]
    lines       = pdf_data["lines"]
    total_qty   = sum(ln["quantity"] for ln in lines)
    total_amt   = sum(ln["line_total"] for ln in lines)
    line_count  = len(lines)

    with conn.cursor() as cur:
        # 1. email_log
        cur.execute("""
            INSERT INTO tnbike.email_log
                (message_id, from_address, received_at, attachment_name,
                 so_number, processing_status)
            VALUES (%s, %s, %s, %s, %s, 'SUCCESS')
            ON CONFLICT (message_id) DO UPDATE
                SET processing_status = 'SUCCESS',
                    processed_at      = NOW()
        """, (
            eml_data["message_id"],
            eml_data["from_address"],
            eml_data["received_at"],
            eml_data["attachment_name"],
            so_number,
        ))

        # 2. sales_order
        cur.execute("""
            INSERT INTO tnbike.sales_order
                (so_number, invoice_symbol, order_date, customer_code,
                 total_amount, total_quantity, line_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id
        """, (
            so_number,
            "C26TTN",          # ký hiệu hóa đơn năm 2026
            order_date,
            customer_code,
            total_amt,
            total_qty,
            line_count,
        ))
        order_id = cur.fetchone()[0]

        # 3. order_line (batch insert)
        execute_batch(cur, """
            INSERT INTO tnbike.order_line
                (order_id, so_number, product_code, quantity, unit_price, line_total)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [
            (order_id, so_number,
             ln["product_code"], ln["quantity"], ln["unit_price"], ln["line_total"])
            for ln in lines
        ])

    conn.commit()
    return order_id


# ---------------------------------------------------------------------------
# Ghi lỗi vào email_log
# ---------------------------------------------------------------------------

def log_email_error(conn, eml_data: dict, so_number: str, error_detail: str) -> None:
    """Ghi record lỗi vào email_log."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tnbike.email_log
                (message_id, from_address, received_at, attachment_name,
                 so_number, processing_status, error_detail)
            VALUES (%s, %s, %s, %s, %s, 'ERROR', %s)
            ON CONFLICT (message_id) DO UPDATE
                SET processing_status = 'ERROR',
                    error_detail      = EXCLUDED.error_detail,
                    processed_at      = NOW()
        """, (
            eml_data.get("message_id"),
            eml_data.get("from_address"),
            eml_data.get("received_at"),
            eml_data.get("attachment_name"),
            so_number or "",
            error_detail[:1000],    # giới hạn độ dài
        ))
    conn.commit()


# ---------------------------------------------------------------------------
# Populate fact_sales (chạy 1 lần sau khi xử lý xong toàn bộ)
# ---------------------------------------------------------------------------

FACT_SALES_INSERT = """
INSERT INTO tnbike.fact_sales (
    order_date, fiscal_year, fiscal_quarter, fiscal_month, week_of_year,
    so_number, order_id, line_id,
    customer_code, customer_name, province_id, province_name, region,
    product_code, product_name, color,
    line_id_fk, line_name, group_code, group_name,
    quantity, unit_price, line_total
)
SELECT
    so.order_date,
    EXTRACT(YEAR    FROM so.order_date)::SMALLINT,
    EXTRACT(QUARTER FROM so.order_date)::SMALLINT,
    EXTRACT(MONTH   FROM so.order_date)::SMALLINT,
    EXTRACT(WEEK    FROM so.order_date)::SMALLINT,
    ol.so_number,
    ol.order_id,
    ol.line_id,
    c.customer_code,
    c.customer_name,
    c.province_id,
    pr.province_name,
    pr.region,
    p.product_code,
    p.product_name,
    p.color,
    p.line_id,
    pl.line_name,
    pg.group_code,
    pg.group_name,
    ol.quantity,
    ol.unit_price,
    ol.line_total
FROM tnbike.order_line ol
JOIN tnbike.sales_order   so ON so.order_id      = ol.order_id
JOIN tnbike.customer       c ON c.customer_code   = so.customer_code
LEFT JOIN tnbike.province  pr ON pr.province_id   = c.province_id
JOIN tnbike.product        p  ON p.product_code   = ol.product_code
LEFT JOIN tnbike.product_line pl ON pl.line_id    = p.line_id
LEFT JOIN tnbike.product_group pg ON pg.group_code = pl.group_code
WHERE so.fiscal_year = 2026
  AND so.fiscal_month = 3
  AND NOT EXISTS (
      SELECT 1 FROM tnbike.fact_sales fs WHERE fs.line_id = ol.line_id
  )
"""


def populate_fact_sales(conn) -> int:
    """
    INSERT tất cả dòng T3/2026 từ order_line vào fact_sales.
    Dùng NOT EXISTS để tránh duplicate nếu chạy lại pipeline.
    Trả về số dòng đã insert.
    """
    with conn.cursor() as cur:
        cur.execute(FACT_SALES_INSERT)
        count = cur.rowcount
    conn.commit()
    return count
