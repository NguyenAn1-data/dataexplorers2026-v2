"""
clean_all.py — Pipeline cleaning HỢP NHẤT cho tnbike_db (PostgreSQL)

Gộp toàn bộ các bước cleaning đã thực hiện trước đó:
  1. Xóa fact_sales.fact_id NULL (column-shift)
  2. Tính lại fiscal_year/month/quarter từ order_date
  3. Chuẩn hóa bảng province: thêm tỉnh thiếu, merge typo/duplicate
  4. Fill province_id/name/region trong fact_sales từ customer
  5. Chuẩn hóa typo province_name
  6. Thêm product_line mới + map product.line_id theo keyword
  7. Fill fact_sales.line_id_fk/line_name/group_code/group_name
  8. Fix product.unit 'Ngày' → 'Chiếc'
  9. Rebuild view v_trend_monthly (YoY/MoM self-join chính xác)
 10. Validation cuối + báo cáo tổng quan

Idempotent: chạy nhiều lần không hỏng dữ liệu.
"""

import psycopg2
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DB = dict(
    host="localhost", port=5432, dbname="tnbike_db",
    user="postgres", password="123456",
    options="-c search_path=tnbike,public",
)

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số mapping
# ─────────────────────────────────────────────────────────────────────────────
NEW_PROVINCES = [
    ("Bình Thuận", "Miền Nam"),
    ("Bình Dương", "Miền Nam"),
    ("Kiên Giang", "Miền Nam"),
    ("Quảng Bình", "Miền Trung"),
]

# Tên sai → tên chuẩn (áp dụng cho fact_sales và province master)
PROV_NAME_FIXES = [
    ("Ha Noi", "Hà Nội"),
    ("Hà Nộ", "Hà Nội"),
    ("Hà Nôi", "Hà Nội"),
    ("Hoà Bình", "Hòa Bình"),
    ("Thanh Hoá", "Thanh Hóa"),
    ("Hưng yên", "Hưng Yên"),
    ("Hưng Yên ", "Hưng Yên"),
    ("Bình Dướng", "Bình Dương"),
    ("TP. Hồ Chí Minh", "Hồ Chí Minh"),
    ("TP.HCM", "Hồ Chí Minh"),
    ("Tp.HCM", "Hồ Chí Minh"),
    ("HCM", "Hồ Chí Minh"),
    ("TP Đà Nẵng", "Đà Nẵng"),
]

# Tỉnh sai/trùng (province_id cũ → tên tỉnh chuẩn để merge sang)
PROV_MERGE_BY_NAME = {
    10: "Hà Nội", 18: "Hải Dương", 16: "Hưng Yên", 15: "Hưng Yên",
    39: "Quảng Ninh", 28: "Nghệ An", 51: "Thanh Hóa", 60: "Hà Tĩnh",
    61: "Thanh Hóa", 47: "Đà Nẵng",
    5: "Hải Dương", 6: "Bắc Ninh", 17: "Quảng Ninh", 21: "Quảng Nam",
    22: "Thanh Hóa", 23: "Hải Dương", 25: "Thanh Hóa", 31: "Bình Thuận",
    32: "Kiên Giang", 34: "Thanh Hóa", 35: "Hà Nam", 42: "Thanh Hóa",
    43: "Thừa Thiên Huế", 44: "Hưng Yên", 45: "Hải Dương", 46: "Hải Phòng",
    49: "Thái Nguyên", 50: "Quảng Nam", 55: "Bắc Giang", 56: "Bình Dương",
    59: "Thái Bình", 63: "Điện Biên", 64: "Quảng Ninh", 65: "Nghệ An",
    67: "Vĩnh Phúc", 68: "Thái Bình", 71: "Thanh Hóa", 72: "Hải Phòng",
    74: "Quảng Bình",
}

# Product line cần thêm (line_name, group_code)
NEW_LINES = [
    ("Xe SK 20", "CITYBIKE_P"), ("Xe SK 24", "CITYBIKE_P"),
    ("Xe CPD 700C", "SPORTBIKE_A"), ("Xe GN 2.0 700C", "CITYBIKE_P"),
    ("Xe MS 27.5", "SPORTBIKE_S"), ("Xe MTB 20-03", "KIDBIKE_1"),
    ("Xe Batwheels 12", "KIDBIKE_2"), ("Xe Batwheels 16", "KIDBIKE_2"),
    ("Xe We Bare Bears 12", "KIDBIKE_2"), ("Xe We Bare Bears 16", "KIDBIKE_2"),
    ("Xe Tom & Jerry 14", "KIDBIKE_2"), ("Xe REX", "SPORTBIKE_S"),
    ("Xe Nam 0209", "CITYBIKE_P"), ("Xe Nữ 0209", "CITYBIKE_P"),
    ("Xe Unite 20", "KIDBIKE_1"), ("Xe Unite 26", "CITYBIKE_P"),
    ("Xe Chưa phân loại", "CITYBIKE_P"),
]

# Keyword trong product_name → line_name (thứ tự ưu tiên: cụ thể → tổng quát)
KEYWORD_MAP = [
    ("LD 26 Pastel", "Xe LD 26"), ("LD 26 We Bare Bears", "Xe LD 26"),
    ("LD 26", "Xe LD 26"), ("LD 24-01", "Xe LD 24-01_2023"),
    ("LD 24-02", "Xe LD 24-02"), ("Super 26 S", "Xe Super 26"),
    ("Super 26", "Xe Super 26"), ("MTB 26-02", "Xe MTB 26 02"),
    ("MTB 26-05", "Xe MTB 26-05_2023"), ("MTB 26-07", "Xe MTB 26-07"),
    ("MTB 24-03", "Xe MTB 24-03"), ("MTB 24-04", "Xe MTB 24-04"),
    ("MTB 20-03", "Xe MTB 20-03"), ("MTB 20-04", "Xe MTB 20-04"),
    ("MTB 20-05", "Xe MTB 20-05"), ("MTB SPD 27.5", "Xe MTB SPD 27.5"),
    ("MTB Cyber 27.5", "Xe MTB Cyber 27.5"), ("Road RPD 700C", "Xe Road RPD 700C"),
    ("Touring Blade 700C", "Xe Touring Blade 700C"), ("CPD 700C", "Xe CPD 700C"),
    ("GRX 2.0", "Xe GRX AT 27.5_2.0"), ("GRX AT", "Xe GRX AT 27.5_2.0"),
    ("GN 2.0 700C", "Xe GN 2.0 700C"),
    ("GN 06-26 2.0 Pro Shimano", "Xe GN 06-26 2.0 Pro Shimano"),
    ("GN 06-26 2.0 Pro", "Xe GN 06-26 2.0 Pro"),
    ("GN 06-27 2.0 Pro Shimano", "Xe GN 06-27 2.0 Pro Shimano"),
    ("GN 06-27 2.0 Pro", "Xe GN 06-27 2.0 Pro"),
    ("GN 06-26 2.0", "Xe GN 06-26 2.0"), ("GN 06-27 2.0", "Xe GN 06-27 2.0"),
    ("GN 06-24 2.0", "Xe GN 06-24 2.0"), ("GN 06-26", "Xe GN 06-26"),
    ("GN 06-27", "Xe GN 06-27"), ("GN 06-24", "Xe GN 06-24"),
    ("GN 06 26", "Xe GN 06-26"), ("GN 05-26", "Xe GN 05-26"),
    ("GN 05-27", "Xe GN 05-27"), ("MS Superman 27.5", "Xe MS 27.5"),
    ("MS 27.5", "Xe MS 27.5"), ("SK 20", "Xe SK 20"), ("SK 24", "Xe SK 24"),
    ("Bubbles 20", "Xe Neo 20-02 Bubble"), ("Neo 20-02", "Xe Neo 20-02"),
    ("Neo 20-03", "Xe Neo 20-03"), ("Neo 2004", "Xe Neo 2004"),
    ("Puppy 20", "Xe Puppy 20"), ("MTB 26 02", "Xe MTB 26 02"),
    ("Highway 27.5", "Xe Highway 27.5"), ("New 26", "Xe New 26"),
    ("New 24", "Xe New 24"), ("219-05-26", "Xe 219-05-26"),
    ("219-24", "Xe 219-24"), ("219-26", "Xe 219-26"),
    ("đạp đôi 26", "Xe đạp đôi 26"), ("M2601 Shimano", "Xe M2601 Shimano"),
    ("M2601", "Xe M2601"), ("SLX 26", "Xe SLX 26-01"),
    ("FLASH", "Xe FLASH (IP - Bản quyền)"), ("Super 24", "Xe Super 24"),
    ("GN 2.0 20 DC", "Xe GN 06 2.0 20 DC (IP - Bản quyền)"),
    ("GN 06 20 2024", "Xe GN 06 20 2024"), ("GN 06 20", "Xe GN 06 20"),
    ("TE 16 Ben 10", "Xe TE 16 Ben 10 (IP - Bản quyền)"),
    ("Teen Titans", "Xe TE 16 Teen Titans Go (IP - Bản quyền)"),
    ("TE 1602", "Xe TE 1602"), ("TE 16-03", "Xe TE 16-03"),
    ("TE 16-04", "Xe TE 16-04"), ("TE 1605", "Xe TE 1605"),
    ("TE Super 20", "Xe TE Super 20"), ("Batwheels 12", "Xe Batwheels 12"),
    ("Batwheels 16", "Xe Batwheels 16"),
    ("We Bare Bears 12", "Xe We Bare Bears 12"),
    ("We Bare Bears 16", "Xe We Bare Bears 16"),
    ("Tom & Jerry 14", "Xe Tom & Jerry 14"),
    ("Bunny 12", "Xe Bunny 12"), ("Bunny 16", "Xe Bunny 16"),
    ("Love 12", "Xe Love 12"), ("Love 16", "Xe Love 16"),
    ("Robot 16", "Xe Robot 16"), ("Spaceboy 12", "Xe Spaceboy 12"),
    ("Spaceboy 16", "Xe Spaceboy 16"), ("TE 12 Princess", "Xe TE 12 Princess"),
    ("TE 16 Princess", "Xe TE 16 Princess"), ("TE 16 RB Jenny", "Xe TE 16 RB Jenny"),
    ("TE 20 Kitten", "Xe TE 20 Kitten"),
    ("Batman12", "Xe TE Batman12 (IP - Bản quyền)"),
    ("Batman16", "Xe TE Batman16 (IP - Bản quyền)"),
    ("Powerpuff Girls 12", "Xe TE Powerpuff Girls 12 (IP - Bản quyền)"),
    ("Powerpuff Girls 16", "Xe TE Powerpuff Girls 16 (IP - Bản quyền)"),
    ("Super Man 12", "Xe TE Super Man 12 (IP - Bản quyền)"),
    ("Super Man 16", "Xe TE Super Man 16 (IP - Bản quyền)"),
    ("Wonder Woman 20", "Xe TE Wonder Woman 20 (IP - Bản quyền)"),
    ("REX", "Xe REX"), ("nam 0209", "Xe Nam 0209"), ("nữ 0209", "Xe Nữ 0209"),
    ("Nữ Lốp", "Xe Nữ"), ("Xe Nam", "Xe Nam"), ("Xe Nữ", "Xe Nữ"),
    ("Unite 20", "Xe Unite 20"), ("Unite 26", "Xe Unite 26"),
    ("M 27-01", "Xe M 27-01"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def banner(t):
    print("\n" + "=" * 70)
    print(f"  {t}")
    print("=" * 70)


def section(t):
    print(f"\n── {t} " + "─" * (66 - len(t)))


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────
def main():
    t0 = datetime.now()
    print(f"START: {t0:%Y-%m-%d %H:%M:%S}")
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor()

    def fetch_one(sql, p=None):
        cur.execute(sql, p)
        return cur.fetchone()[0]

    stats = {}

    # ── BƯỚC 1: Xóa fact_id NULL ─────────────────────────────────────────────
    banner("BƯỚC 1: Xóa fact_sales.fact_id NULL (column-shift)")
    n = fetch_one("SELECT COUNT(*) FROM tnbike.fact_sales WHERE fact_id IS NULL")
    print(f"  fact_id NULL hiện có: {n}")
    cur.execute("DELETE FROM tnbike.fact_sales WHERE fact_id IS NULL")
    print(f"  Đã xóa: {cur.rowcount} dòng")
    stats["b1_deleted"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 2: Recalc fiscal ────────────────────────────────────────────────
    banner("BƯỚC 2: Tính lại fiscal_year/month/quarter từ order_date")
    cur.execute("""
        UPDATE tnbike.fact_sales
        SET fiscal_year    = EXTRACT(YEAR    FROM order_date)::int,
            fiscal_month   = EXTRACT(MONTH   FROM order_date)::int,
            fiscal_quarter = EXTRACT(QUARTER FROM order_date)::int
        WHERE order_date IS NOT NULL
          AND (fiscal_year    IS DISTINCT FROM EXTRACT(YEAR    FROM order_date)::int
            OR fiscal_month   IS DISTINCT FROM EXTRACT(MONTH   FROM order_date)::int
            OR fiscal_quarter IS DISTINCT FROM EXTRACT(QUARTER FROM order_date)::int)
    """)
    print(f"  Đã cập nhật: {cur.rowcount} dòng")
    stats["b2_fiscal"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 3: Chuẩn hóa province master ────────────────────────────────────
    banner("BƯỚC 3: Chuẩn hóa bảng province (thêm thiếu + merge duplicate)")

    section("3a. Thêm tỉnh còn thiếu")
    added_prov = 0
    for pname, region in NEW_PROVINCES:
        cur.execute("SELECT province_id FROM tnbike.province WHERE province_name = %s", (pname,))
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO tnbike.province (province_name, region) VALUES (%s, %s)",
            (pname, region),
        )
        added_prov += 1
        print(f"  [NEW] {pname} ({region})")
    if added_prov == 0:
        print("  Không có tỉnh nào cần thêm (đã đủ)")
    stats["b3_prov_added"] = added_prov

    section("3b. Sửa tên 'TP. Hồ Chí Minh' → 'Hồ Chí Minh'")
    cur.execute("""
        UPDATE tnbike.province
        SET province_name = 'Hồ Chí Minh', region = 'Miền Nam'
        WHERE province_name IN ('TP. Hồ Chí Minh', 'TP.HCM', 'Tp.HCM', 'HCM')
    """)
    print(f"  Đã đổi tên: {cur.rowcount} dòng")
    conn.commit()

    section("3c. Áp typo fix lên province master")
    for wrong, right in PROV_NAME_FIXES:
        cur.execute("""
            UPDATE tnbike.province SET province_name = %s
            WHERE TRIM(province_name) = %s AND province_name IS DISTINCT FROM %s
        """, (right, wrong.strip(), right))
        if cur.rowcount:
            print(f"  '{wrong}' → '{right}': {cur.rowcount}")
    conn.commit()

    section("3d. Merge province_id sai/trùng về tỉnh chuẩn")
    cur.execute("SELECT province_id, province_name FROM tnbike.province")
    name_to_id = {r[1]: r[0] for r in cur.fetchall()}

    merged_cust = merged_fs = 0
    for old_id, target_name in PROV_MERGE_BY_NAME.items():
        new_id = name_to_id.get(target_name)
        if new_id is None or new_id == old_id:
            continue
        cur.execute("SELECT province_name, region FROM tnbike.province WHERE province_id = %s", (new_id,))
        row = cur.fetchone()
        if not row:
            continue
        nname, nregion = row

        cur.execute(
            "UPDATE tnbike.customer SET province_id = %s WHERE province_id = %s",
            (new_id, old_id),
        )
        merged_cust += cur.rowcount
        cur.execute("""
            UPDATE tnbike.fact_sales
            SET province_id = %s, province_name = %s, region = %s
            WHERE province_id = %s
        """, (new_id, nname, nregion, old_id))
        merged_fs += cur.rowcount
    print(f"  Merged: customer={merged_cust}, fact_sales={merged_fs}")
    stats["b3_merged_cust"] = merged_cust
    stats["b3_merged_fs"] = merged_fs
    conn.commit()

    section("3e. Xóa province_id sai/trùng nếu không còn tham chiếu")
    deleted = 0
    for old_id in PROV_MERGE_BY_NAME:
        nc = fetch_one("SELECT COUNT(*) FROM tnbike.customer WHERE province_id = %s", (old_id,))
        nf = fetch_one("SELECT COUNT(*) FROM tnbike.fact_sales WHERE province_id = %s", (old_id,))
        if nc == 0 and nf == 0:
            cur.execute("DELETE FROM tnbike.province WHERE province_id = %s", (old_id,))
            deleted += cur.rowcount
    print(f"  Đã xóa: {deleted} bản ghi province")
    stats["b3_prov_deleted"] = deleted
    conn.commit()

    # ── BƯỚC 4: Fill province_id NULL trong fact_sales ───────────────────────
    banner("BƯỚC 4: Fill province trong fact_sales từ customer")
    cur.execute("""
        UPDATE tnbike.fact_sales fs
        SET province_id   = c.province_id,
            province_name = p.province_name,
            region        = p.region
        FROM tnbike.customer c
        JOIN tnbike.province p ON p.province_id = c.province_id
        WHERE fs.customer_code = c.customer_code
          AND fs.province_id IS NULL
    """)
    print(f"  Đã fill: {cur.rowcount} dòng")
    stats["b4_filled"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 5: Áp typo fix province_name trong fact_sales + sync ───────────
    banner("BƯỚC 5: Chuẩn hóa province_name trong fact_sales")
    total_fixed = 0
    for wrong, right in PROV_NAME_FIXES:
        cur.execute("""
            UPDATE tnbike.fact_sales SET province_name = %s
            WHERE TRIM(province_name) = %s AND province_name IS DISTINCT FROM %s
        """, (right, wrong.strip(), right))
        total_fixed += cur.rowcount
    cur.execute(r"""
        UPDATE tnbike.fact_sales
        SET province_name = REGEXP_REPLACE(province_name, '[\n\r\t]+', ' ', 'g')
        WHERE province_name ~ '[\n\r\t]'
    """)
    total_fixed += cur.rowcount
    print(f"  Fix typo: {total_fixed} dòng")

    # Sync với master
    cur.execute("""
        UPDATE tnbike.fact_sales fs
        SET province_name = p.province_name, region = p.region
        FROM tnbike.province p
        WHERE fs.province_id = p.province_id
          AND (fs.province_name IS DISTINCT FROM p.province_name
            OR fs.region        IS DISTINCT FROM p.region)
    """)
    print(f"  Sync với master: {cur.rowcount} dòng")
    stats["b5_prov_synced"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 6: Product line ─────────────────────────────────────────────────
    banner("BƯỚC 6: Thêm product_line + map product.line_id")

    section("6a. Thêm product_line mới")
    line_id_map = {}
    added_lines = 0
    for line_name, group_code in NEW_LINES:
        cur.execute("SELECT line_id FROM tnbike.product_line WHERE line_name = %s", (line_name,))
        row = cur.fetchone()
        if row:
            line_id_map[line_name] = row[0]
        else:
            cur.execute(
                "INSERT INTO tnbike.product_line (line_name, group_code) VALUES (%s, %s) RETURNING line_id",
                (line_name, group_code),
            )
            line_id_map[line_name] = cur.fetchone()[0]
            added_lines += 1
    print(f"  Đã thêm: {added_lines} dòng product_line mới")
    stats["b6_lines_added"] = added_lines

    cur.execute("SELECT line_id, line_name FROM tnbike.product_line")
    for lid, lname in cur.fetchall():
        line_id_map[lname] = lid
    conn.commit()

    section("6b. Map product.line_id (NULL) theo keyword")
    cur.execute("SELECT product_code, product_name FROM tnbike.product WHERE line_id IS NULL")
    null_products = cur.fetchall()
    print(f"  Cần map: {len(null_products)} sản phẩm")

    fallback_lid = line_id_map.get("Xe Chưa phân loại")
    fixed_prod = 0
    for product_code, product_name in null_products:
        pname_lc = (product_name or "").lower()
        lid = None
        for keyword, line_name in KEYWORD_MAP:
            if keyword.lower() in pname_lc:
                lid = line_id_map.get(line_name)
                if lid:
                    break
        if lid is None:
            lid = fallback_lid
        if lid:
            cur.execute(
                "UPDATE tnbike.product SET line_id = %s WHERE product_code = %s AND line_id IS NULL",
                (lid, product_code),
            )
            fixed_prod += cur.rowcount
    print(f"  Đã update product.line_id: {fixed_prod}")
    stats["b6_prod_mapped"] = fixed_prod
    conn.commit()

    section("6c. Fill fact_sales line_id_fk/line_name/group_code/group_name")
    cur.execute("""
        UPDATE tnbike.fact_sales fs
        SET line_id_fk = p.line_id,
            line_name  = pl.line_name,
            group_code = pl.group_code,
            group_name = pg.group_name
        FROM tnbike.product p
        JOIN tnbike.product_line  pl ON p.line_id     = pl.line_id
        JOIN tnbike.product_group pg ON pl.group_code = pg.group_code
        WHERE fs.product_code = p.product_code
          AND (fs.line_id_fk IS NULL
            OR fs.group_code IS NULL
            OR fs.line_name  IS NULL
            OR fs.group_name IS NULL)
    """)
    print(f"  Đã fill fact_sales: {cur.rowcount}")
    stats["b6_fs_filled"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 7: product.unit ────────────────────────────────────────────────
    banner("BƯỚC 7: Fix product.unit 'Ngày' → 'Chiếc'")
    cur.execute("UPDATE tnbike.product SET unit = 'Chiếc' WHERE unit = 'Ngày'")
    print(f"  Đã fix: {cur.rowcount}")
    stats["b7_unit"] = cur.rowcount
    conn.commit()

    # ── BƯỚC 8: Rebuild v_trend_monthly ─────────────────────────────────────
    banner("BƯỚC 8: Rebuild view v_trend_monthly (YoY/MoM self-join)")
    cur.execute("DROP VIEW IF EXISTS tnbike.v_trend_monthly CASCADE")
    cur.execute("""
        CREATE VIEW tnbike.v_trend_monthly AS
        WITH monthly AS (
            SELECT
                fiscal_year, fiscal_month, fiscal_quarter,
                TO_DATE(fiscal_year::text || LPAD(fiscal_month::text,2,'0') || '01', 'YYYYMMDD') AS month_date,
                'T' || fiscal_month || '/' || fiscal_year                  AS month_label,
                fiscal_year * 100 + fiscal_month                           AS sort_key,
                COUNT(DISTINCT so_number)                                  AS total_orders,
                COUNT(DISTINCT customer_code)                              AS active_dealers,
                SUM(quantity)                                              AS total_qty,
                ROUND(SUM(line_total)::numeric / 1e9, 3)                   AS revenue_ty,
                ROUND(AVG(unit_price)::numeric)                            AS avg_unit_price,
                COUNT(*)                                                   AS line_items
            FROM tnbike.fact_sales
            GROUP BY fiscal_year, fiscal_month, fiscal_quarter
        )
        SELECT m.*,
            ly.revenue_ty AS revenue_ty_ly,
            ly.total_orders AS orders_ly,
            ly.active_dealers AS dealers_ly,
            ly.total_qty AS qty_ly,
            CASE WHEN COALESCE(ly.revenue_ty, 0) > 0
                 THEN ROUND((m.revenue_ty - ly.revenue_ty) / ly.revenue_ty * 100, 1)
                 ELSE NULL END AS yoy_growth_pct,
            pm.revenue_ty AS revenue_ty_pm,
            CASE WHEN COALESCE(pm.revenue_ty, 0) > 0
                 THEN ROUND((m.revenue_ty - pm.revenue_ty) / pm.revenue_ty * 100, 1)
                 ELSE NULL END AS mom_growth_pct
        FROM monthly m
        LEFT JOIN monthly ly
               ON ly.fiscal_year = m.fiscal_year - 1
              AND ly.fiscal_month = m.fiscal_month
        LEFT JOIN monthly pm
               ON (m.fiscal_month > 1
                   AND pm.fiscal_year = m.fiscal_year
                   AND pm.fiscal_month = m.fiscal_month - 1)
               OR (m.fiscal_month = 1
                   AND pm.fiscal_year = m.fiscal_year - 1
                   AND pm.fiscal_month = 12)
        ORDER BY m.sort_key
    """)
    print("  ✓ View v_trend_monthly đã rebuild")
    conn.commit()

    # ── VALIDATION CUỐI ─────────────────────────────────────────────────────
    banner("VALIDATION CUỐI — Kiểm tra integrity")
    checks = [
        ("fact_sales: fact_id NULL",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE fact_id IS NULL", 0),
        ("fact_sales: order_date NULL",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE order_date IS NULL", 0),
        ("fact_sales: fiscal_year sai",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE fiscal_year IS NULL OR fiscal_year::text !~ '^20[0-9]{2}$'", 0),
        ("fact_sales: fiscal_year != EXTRACT(order_date)",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE EXTRACT(YEAR FROM order_date)::int != fiscal_year", 0),
        ("fact_sales: line_id_fk NULL",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE line_id_fk IS NULL", 0),
        ("fact_sales: group_code NULL",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE group_code IS NULL", 0),
        ("fact_sales: line_total != qty*price (>50 VND)",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE ABS(line_total - quantity * unit_price) > 50", 0),
        ("product: line_id NULL",
         "SELECT COUNT(*) FROM tnbike.product WHERE line_id IS NULL", 0),
        ("product: unit='Ngày'",
         "SELECT COUNT(*) FROM tnbike.product WHERE unit = 'Ngày'", 0),
        ("fact_sales: province_id NULL (warn)",
         "SELECT COUNT(*) FROM tnbike.fact_sales WHERE province_id IS NULL", -1),
    ]
    fail = warn = ok = 0
    for label, sql, expected in checks:
        v = fetch_one(sql)
        if expected == -1:
            tag = "[WARN]" if v > 0 else "[OK]  "
            warn += 1 if v > 0 else 0
            ok += 1 if v == 0 else 0
        elif v == expected:
            tag = "[OK]  "
            ok += 1
        else:
            tag = "[FAIL]"
            fail += 1
        print(f"  {tag} {label}: {v}")

    # ── BÁO CÁO TỔNG QUAN ───────────────────────────────────────────────────
    banner("BÁO CÁO DỮ LIỆU SAU CLEAN")
    cur.execute("""
        SELECT COUNT(*), MIN(order_date), MAX(order_date),
               ROUND(SUM(line_total)::numeric/1e9, 2),
               COUNT(DISTINCT customer_code), COUNT(DISTINCT product_code)
        FROM tnbike.fact_sales
    """)
    r = cur.fetchone()
    print(f"  fact_sales       : {r[0]:,} dòng")
    print(f"  Khoảng thời gian : {r[1]} → {r[2]}")
    print(f"  Tổng doanh thu   : {r[3]} tỷ VND")
    print(f"  KH duy nhất      : {r[4]}")
    print(f"  SP duy nhất      : {r[5]}")

    section("Doanh thu theo tháng")
    cur.execute("""
        SELECT month_label, revenue_ty, total_orders, active_dealers,
               yoy_growth_pct, mom_growth_pct
        FROM tnbike.v_trend_monthly ORDER BY sort_key
    """)
    print(f"  {'Tháng':10} | {'DT (tỷ)':>8} | {'Đơn':>5} | {'KH':>4} | {'YoY%':>6} | {'MoM%':>6}")
    print("  " + "-" * 60)
    for row in cur.fetchall():
        bar = "█" * min(int(float(row[1] or 0) * 2), 25)
        yoy = f"{row[4]:>5}" if row[4] is not None else "    -"
        mom = f"{row[5]:>5}" if row[5] is not None else "    -"
        print(f"  {str(row[0]):10} | {str(row[1]):>8} | {row[2]:>5} | {row[3]:>4} | {yoy:>6} | {mom:>6} {bar}")

    section("Doanh thu theo nhóm SP")
    cur.execute("""
        SELECT group_code, group_name, COUNT(*), ROUND(SUM(line_total)::numeric/1e9, 2)
        FROM tnbike.fact_sales WHERE group_code IS NOT NULL
        GROUP BY group_code, group_name ORDER BY 4 DESC
    """)
    for row in cur.fetchall():
        print(f"  {str(row[0]):15s} | {str(row[1]):25s} | {row[2]:>6} dòng | {row[3]:>6.2f} tỷ")

    section("Doanh thu theo vùng")
    cur.execute("""
        SELECT region, COUNT(DISTINCT customer_code), ROUND(SUM(line_total)::numeric/1e9, 2)
        FROM tnbike.fact_sales WHERE region IS NOT NULL
        GROUP BY region ORDER BY 3 DESC
    """)
    for row in cur.fetchall():
        print(f"  {str(row[0]):12s} | {row[1]:>4} KH | {row[2]:>6} tỷ VND")

    # ── KẾT THÚC ────────────────────────────────────────────────────────────
    banner("TỔNG KẾT PIPELINE")
    print(f"  B1 Xóa fact_id NULL          : {stats['b1_deleted']}")
    print(f"  B2 Recalc fiscal             : {stats['b2_fiscal']}")
    print(f"  B3 Province thêm/merge/xóa   : +{stats['b3_prov_added']} / cust={stats['b3_merged_cust']} fs={stats['b3_merged_fs']} / -{stats['b3_prov_deleted']}")
    print(f"  B4 Fill province fact_sales  : {stats['b4_filled']}")
    print(f"  B5 Sync province_name        : {stats['b5_prov_synced']}")
    print(f"  B6 Line: +{stats['b6_lines_added']} / map prod={stats['b6_prod_mapped']} / fill fs={stats['b6_fs_filled']}")
    print(f"  B7 Fix unit Ngày→Chiếc       : {stats['b7_unit']}")
    print(f"\n  Validation: {ok} OK | {warn} WARN | {fail} FAIL")
    print(f"  Thời gian chạy: {(datetime.now() - t0).total_seconds():.1f}s")
    print("\nHOÀN THÀNH ✓\n")

    cur.close()
    conn.close()
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
