"""
Push tất cả forecast tables vào PostgreSQL schema tnbike để Power BI đọc trực tiếp.

Tables tạo mới (DROP & CREATE):
  tnbike_forecast.forecast_total       — tổng công ty × 3 tháng × 3 kịch bản
  tnbike_forecast.forecast_group       — 5 group × 3 tháng × 3 kịch bản
  tnbike_forecast.forecast_sku         — SKU × 3 tháng (base scenario)
  tnbike_forecast.forecast_top20_sku   — top 20 SKU dự kiến bán chạy Q2/26
  tnbike_forecast.forecast_color       — color × group share Q2/26
  tnbike_forecast.color_trend          — color trend Q1/25 vs Q1/26 (cho dashboard)
  tnbike_forecast.forecast_slow_sku    — SKU bán chậm / nguy cơ giảm
  tnbike_forecast.dealer_score         — 798 đại lý: BG/NBD scores + tier
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np
import psycopg2
from psycopg2.extras import execute_values

DATA = os.path.join(os.path.dirname(__file__), "data")
CONN = dict(host="localhost", dbname="tnbike_db", user="postgres", password="123456")

# Định nghĩa từng bảng: name, schema DDL, parquet file, columns mapping
TABLES = [
    {
        "name": "forecast_total",
        "parquet": "forecast_total_q2.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_total (
                year_month VARCHAR(7),
                scenario VARCHAR(20),
                revenue NUMERIC(18,2),
                qty NUMERIC(18,2),
                orders NUMERIC(18,2),
                month_factor NUMERIC(6,3),
                scenario_factor NUMERIC(6,3)
            )
        """,
        "cols": ["year_month","scenario","revenue","qty","orders","month_factor","scenario_factor"],
    },
    {
        "name": "forecast_group",
        "parquet": "forecast_group_q2.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_group (
                year_month VARCHAR(7),
                group_code VARCHAR(20),
                group_name VARCHAR(100),
                scenario VARCHAR(20),
                revenue NUMERIC(18,2),
                qty NUMERIC(18,2)
            )
        """,
        "cols": ["year_month","group_code","group_name","scenario","revenue","qty"],
    },
    {
        "name": "forecast_sku",
        "parquet": "forecast_sku_q2.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_sku (
                product_code VARCHAR(20),
                product_name VARCHAR(200),
                color VARCHAR(50),
                line_id INTEGER,
                line_name VARCHAR(100),
                group_code VARCHAR(20),
                year_month VARCHAR(7),
                revenue NUMERIC(18,2),
                qty NUMERIC(18,2)
            )
        """,
        "cols": ["product_code","product_name","color","line_id_fk","line_name","group_code","year_month","revenue","qty"],
        "col_rename": {"line_id_fk":"line_id"},
    },
    {
        "name": "forecast_top20_sku",
        "parquet": "forecast_top20_sku.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_top20_sku (
                rank INTEGER,
                product_code VARCHAR(20),
                product_name VARCHAR(200),
                color VARCHAR(50),
                line_name VARCHAR(100),
                group_code VARCHAR(20),
                q2_revenue NUMERIC(18,2),
                q2_qty NUMERIC(18,2)
            )
        """,
        "cols": ["rank","product_code","product_name","color","line_name","group_code","q2_revenue","q2_qty"],
    },
    {
        "name": "forecast_color",
        "parquet": "forecast_color_q2.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_color (
                group_code VARCHAR(20),
                color VARCHAR(50),
                q2_revenue NUMERIC(18,2),
                q2_qty NUMERIC(18,2),
                g_total NUMERIC(18,2),
                share_pct NUMERIC(8,4)
            )
        """,
        "cols": ["group_code","color","q2_revenue","q2_qty","g_total","share_pct"],
    },
    {
        "name": "color_trend",
        "parquet": "color_trend.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.color_trend (
                color VARCHAR(50),
                rev_25 NUMERIC(18,2),
                qty_25 NUMERIC(18,2),
                rev_26 NUMERIC(18,2),
                qty_26 NUMERIC(18,2),
                share_25 NUMERIC(8,4),
                share_26 NUMERIC(8,4),
                share_delta NUMERIC(8,4)
            )
        """,
        "cols": ["color","rev_25","qty_25","rev_26","qty_26","share_25","share_26","share_delta"],
    },
    {
        "name": "forecast_slow_sku",
        "parquet": "forecast_slow_sku.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.forecast_slow_sku (
                product_code VARCHAR(20),
                product_name VARCHAR(200),
                color VARCHAR(50),
                line_name VARCHAR(100),
                group_code VARCHAR(20),
                q1_26_rev NUMERIC(18,2),
                q1_26_qty NUMERIC(18,2),
                t12_qty NUMERIC(18,2),
                t3_qty NUMERIC(18,2),
                q1_25_qty NUMERIC(18,2),
                q2_pred_rev NUMERIC(18,2),
                q2_pred_qty NUMERIC(18,2),
                t3_drop BOOLEAN,
                dead_in_2026 BOOLEAN,
                pred_drop BOOLEAN,
                slow_mover BOOLEAN,
                reasons VARCHAR(50)
            )
        """,
        "cols": ["product_code","product_name","color","line_name","group_code",
                 "q1_26_rev","q1_26_qty","t12_qty","t3_qty","q1_25_qty",
                 "q2_pred_rev","q2_pred_qty","t3_drop","dead_in_2026","pred_drop","slow_mover","reasons"],
    },
    {
        "name": "dealer_score",
        "parquet": "dealer_score.parquet",
        "ddl": """
            CREATE TABLE tnbike_forecast.dealer_score (
                customer_code VARCHAR(20),
                freq_repeat NUMERIC(10,4),
                recency NUMERIC(10,4),
                tenure_days NUMERIC(10,4),
                avg_monetary_hist NUMERIC(18,2),
                p_order_30d NUMERIC(8,6),
                p_alive NUMERIC(8,6),
                expected_avg_monetary NUMERIC(18,2),
                expected_purchases_90d NUMERIC(10,4),
                expected_revenue_q2 NUMERIC(18,2),
                priority_score NUMERIC(8,6),
                tier VARCHAR(20)
            )
        """,
        "cols": ["customer_code","freq_repeat","recency","tenure_days","avg_monetary_hist",
                 "p_order_30d","p_alive","expected_avg_monetary","expected_purchases_90d",
                 "expected_revenue_q2","priority_score","tier"],
    },
]

# Connect và ghi từng bảng
conn = psycopg2.connect(**CONN)
conn.autocommit = False
cur = conn.cursor()

# Tạo schema riêng để KHÔNG lẫn với schema gốc tnbike của BTC
cur.execute("CREATE SCHEMA IF NOT EXISTS tnbike_forecast")
print("✓ schema tnbike_forecast ready")

# Rollback: nếu trước đó đã lỡ ghi vào schema tnbike thì dọn sạch
ROLLBACK_TABLES = ["forecast_total","forecast_group","forecast_sku","forecast_top20_sku",
                   "forecast_color","color_trend","forecast_slow_sku","dealer_score"]
for tbl in ROLLBACK_TABLES:
    cur.execute(f"DROP TABLE IF EXISTS tnbike.{tbl} CASCADE")
print("✓ đã dọn 8 bảng forecast khỏi schema tnbike (nếu tồn tại)")

for t in TABLES:
    print(f"\n→ {t['name']}")
    path = os.path.join(DATA, t["parquet"])
    df = pd.read_parquet(path)
    if "col_rename" in t:
        df = df.rename(columns=t["col_rename"])
    # Reorder. Nếu cột đã được đổi tên thì lấy theo tên mới.
    rename = t.get("col_rename", {})
    cols_in_df = [rename.get(c, c) for c in t["cols"]]
    df = df[cols_in_df].copy()
    # Convert NaN/numpy → Python types for psycopg2
    df = df.where(pd.notnull(df), None)
    # Convert numpy bool to Python bool
    for c in df.columns:
        if df[c].dtype == bool or df[c].dtype == "boolean":
            df[c] = df[c].astype(bool)

    cur.execute(f"DROP TABLE IF EXISTS tnbike_forecast.{t['name']} CASCADE")
    cur.execute(t["ddl"])

    placeholders = ", ".join([f'"{c}"' for c in cols_in_df])
    sql = f"INSERT INTO tnbike_forecast.{t['name']} ({placeholders}) VALUES %s"
    rows = [tuple(None if pd.isna(v) else (bool(v) if isinstance(v, np.bool_) else v) for v in r)
            for r in df.itertuples(index=False, name=None)]
    execute_values(cur, sql, rows, page_size=500)
    print(f"   inserted {len(rows):,} rows")

conn.commit()

# Verify
print("\n" + "=" * 80)
print("VERIFY tables in PostgreSQL")
print("=" * 80)
for t in TABLES:
    cur.execute(f"SELECT COUNT(*) FROM tnbike_forecast.{t['name']}")
    n = cur.fetchone()[0]
    print(f"   tnbike_forecast.{t['name']:25s} {n:>6,} rows")

cur.close(); conn.close()
print("\n✓ Tất cả bảng forecast đã được ghi vào schema tnbike_forecast. Power BI có thể refresh và dùng ngay.")
