"""
Xây các bảng tổng hợp cho Phase C:
- df_total: 6 dòng (1 dòng/tháng) cho tổng công ty
- df_group: (group_code × month) cho 5 nhóm sản phẩm
- df_sku:   (product_code × month) cho 265 SKU
- df_color: (group_code × color × month) cho phân tích màu
- df_dealer_trans: (customer_code × order_date × total) cho BG/NBD

Lưu ra parquet để các script sau dùng lại.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pandas as pd
import psycopg2

CONN_ARGS = dict(host="localhost", dbname="tnbike_db", user="postgres", password="123456")
OUT = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT, exist_ok=True)

conn = psycopg2.connect(**CONN_ARGS)

def read(sql):
    return pd.read_sql(sql, conn)

print("Loading fact_sales ...")
f = read("""
    SELECT fact_id, order_date, fiscal_year, fiscal_month,
           so_number, order_id, customer_code, province_id, region,
           product_code, product_name, color, line_id_fk, line_name, group_code, group_name,
           quantity::float AS quantity, unit_price::float AS unit_price, line_total::float AS line_total
    FROM tnbike.fact_sales
""")
f["order_date"] = pd.to_datetime(f["order_date"])
f["year_month"] = f["order_date"].dt.to_period("M").astype(str)
print(f"  fact rows: {len(f):,}")
print(f"  months: {sorted(f['year_month'].unique())}")

# Tổng công ty
df_total = (f.groupby("year_month")
              .agg(qty=("quantity","sum"),
                   revenue=("line_total","sum"),
                   orders=("so_number","nunique"),
                   lines=("fact_id","count"),
                   active_dealers=("customer_code","nunique"),
                   active_skus=("product_code","nunique"))
              .reset_index().sort_values("year_month"))

# Nhóm sản phẩm
df_group = (f.groupby(["year_month","group_code","group_name"])
              .agg(qty=("quantity","sum"),
                   revenue=("line_total","sum"),
                   orders=("so_number","nunique"),
                   lines=("fact_id","count"))
              .reset_index().sort_values(["group_code","year_month"]))

# SKU
df_sku = (f.groupby(["year_month","product_code","product_name","color","line_id_fk","line_name","group_code"])
            .agg(qty=("quantity","sum"),
                 revenue=("line_total","sum"),
                 orders=("so_number","nunique"))
            .reset_index().sort_values(["product_code","year_month"]))

# Màu trong nhóm
df_color = (f.groupby(["year_month","group_code","color"])
              .agg(qty=("quantity","sum"),
                   revenue=("line_total","sum"))
              .reset_index().sort_values(["group_code","color","year_month"]))

# Giao dịch đại lý (cho BG/NBD)
df_dealer = (f.groupby(["customer_code","order_date","so_number"])
               .agg(amount=("line_total","sum"),
                    qty=("quantity","sum"))
               .reset_index())

for name, d in [("total",df_total),("group",df_group),("sku",df_sku),
                ("color",df_color),("dealer_trans",df_dealer)]:
    path = os.path.join(OUT, f"df_{name}.parquet")
    d.to_parquet(path, index=False)
    print(f"  {name:14s} -> {len(d):>6,} rows  {path}")

print("\n=== df_total ===")
print(df_total.to_string(index=False))

print("\n=== df_group (revenue tỷ VND) ===")
pivot = df_group.pivot(index="group_name", columns="year_month", values="revenue").fillna(0)/1e9
print(pivot.round(2).to_string())

conn.close()
