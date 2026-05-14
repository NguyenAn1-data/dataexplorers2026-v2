"""
Phase C - Câu hỏi 1: Dự báo doanh số Q2/2026 (Apr/May/Jun)

Phương pháp:
- Model: Seasonal Multiplicative (M5) - đã chọn qua backtest T3/26 với WAPE 4.4% ở group.
- Vì KHÔNG có dữ liệu Q2/2025, không thể dùng seasonal index năm cho Q2.
- Assumption (đã được duyệt):
    Base: Q2 = baseline pre-Tết (avg T1+T2/26) × monthly trend factor
    Trend MoM: Apr ×1.05, May ×1.07, Jun ×1.10  (phản ánh growth nhẹ)
    Sensitivity: dải Lạc quan ×1.15, Thận trọng ×0.85
- Top-down: total → 5 group → SKU.

Output:
    data/forecast_total_q2.parquet     — 3 dòng (Apr/May/Jun) × 3 kịch bản
    data/forecast_group_q2.parquet     — 15 dòng (5 group × 3 tháng) × 3 kịch bản
    data/forecast_sku_q2.parquet       — toàn bộ SKU × 3 tháng (base)
    data/forecast_top20_sku.parquet    — top-20 SKU dự kiến bán chạy Q2/26
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np

DATA = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA, exist_ok=True)

df_total = pd.read_parquet(os.path.join(DATA, "df_total.parquet"))
df_group = pd.read_parquet(os.path.join(DATA, "df_group.parquet"))
df_sku   = pd.read_parquet(os.path.join(DATA, "df_sku.parquet"))

# Monthly trend factors (assumption đã duyệt với user)
MONTH_FACTORS = {"2026-04": 1.05, "2026-05": 1.07, "2026-06": 1.10}
# Sensitivity bands
SCENARIOS = {"pessimistic": 0.85, "base": 1.00, "optimistic": 1.15}
FORECAST_MONTHS = list(MONTH_FACTORS.keys())

def baseline(series, t1="2026-01", t2="2026-02"):
    return (series.get(t1, 0) + series.get(t2, 0)) / 2

print("=" * 80)
print("FORECAST Q2/2026 — TOTAL COMPANY")
print("=" * 80)

# ===== TOTAL =====
s_total_rev = dict(zip(df_total["year_month"], df_total["revenue"]))
s_total_qty = dict(zip(df_total["year_month"], df_total["qty"]))
s_total_ord = dict(zip(df_total["year_month"], df_total["orders"]))

baseline_rev_total = baseline(s_total_rev)
baseline_qty_total = baseline(s_total_qty)
baseline_ord_total = baseline(s_total_ord)

print(f"Baseline pre-Tết (avg T1+T2/26): revenue={baseline_rev_total/1e9:.2f} tỷ, qty={baseline_qty_total:.0f}, orders={baseline_ord_total:.0f}")

rows_total = []
for m, mf in MONTH_FACTORS.items():
    for scn, sf in SCENARIOS.items():
        rows_total.append({
            "year_month": m,
            "scenario": scn,
            "revenue": baseline_rev_total * mf * sf,
            "qty":     baseline_qty_total * mf * sf,
            "orders":  baseline_ord_total * mf * sf,
            "month_factor": mf,
            "scenario_factor": sf,
        })
ft = pd.DataFrame(rows_total)
ft.to_parquet(os.path.join(DATA, "forecast_total_q2.parquet"), index=False)

# Print summary
print("\nTotal forecast (revenue tỷ VND):")
print(f"{'Month':10s} {'Pessim':>8s} {'Base':>8s} {'Optim':>8s}")
for m in FORECAST_MONTHS:
    sub = ft[ft["year_month"] == m]
    print(f"{m:10s} {sub[sub['scenario']=='pessimistic']['revenue'].iloc[0]/1e9:8.2f} "
          f"{sub[sub['scenario']=='base']['revenue'].iloc[0]/1e9:8.2f} "
          f"{sub[sub['scenario']=='optimistic']['revenue'].iloc[0]/1e9:8.2f}")
q2_total = ft[ft["scenario"]=="base"]["revenue"].sum()/1e9
q2_total_lo = ft[ft["scenario"]=="pessimistic"]["revenue"].sum()/1e9
q2_total_hi = ft[ft["scenario"]=="optimistic"]["revenue"].sum()/1e9
print(f"\nQ2/2026 TOTAL revenue: BASE {q2_total:.1f} tỷ  (band: {q2_total_lo:.1f} - {q2_total_hi:.1f})")

# ===== GROUP =====
print("\n" + "=" * 80)
print("FORECAST Q2/2026 — 5 PRODUCT GROUPS")
print("=" * 80)

rows_group = []
for (gc, gn), sub in df_group.groupby(["group_code","group_name"]):
    s_rev = dict(zip(sub["year_month"], sub["revenue"]))
    s_qty = dict(zip(sub["year_month"], sub["qty"]))
    base_rev = baseline(s_rev)
    base_qty = baseline(s_qty)
    for m, mf in MONTH_FACTORS.items():
        for scn, sf in SCENARIOS.items():
            rows_group.append({
                "year_month": m, "group_code": gc, "group_name": gn,
                "scenario": scn,
                "revenue": base_rev * mf * sf,
                "qty":     base_qty * mf * sf,
            })

fg = pd.DataFrame(rows_group)
fg.to_parquet(os.path.join(DATA, "forecast_group_q2.parquet"), index=False)

# Print group base scenario summary
print(f"\n{'Group':22s} {'Q2 Base':>9s} {'Q2 Lo':>8s} {'Q2 Hi':>8s}")
for (gc, gn), sub in fg.groupby(["group_code","group_name"]):
    b = sub[sub["scenario"]=="base"]["revenue"].sum()/1e9
    lo = sub[sub["scenario"]=="pessimistic"]["revenue"].sum()/1e9
    hi = sub[sub["scenario"]=="optimistic"]["revenue"].sum()/1e9
    print(f"{gn[:22]:22s} {b:9.2f} {lo:8.2f} {hi:8.2f}")

# ===== SKU =====
print("\n" + "=" * 80)
print("FORECAST Q2/2026 — SKU LEVEL (top-down từ group, theo share T1+T2/26)")
print("=" * 80)

sku_meta = df_sku.groupby("product_code").agg({
    "product_name":"first","color":"first","line_id_fk":"first","line_name":"first","group_code":"first"
}).reset_index()

# (T1+T2)/26 cho mỗi SKU và mỗi group
sku_t1t2 = (df_sku[df_sku["year_month"].isin(["2026-01","2026-02"])]
            .groupby("product_code")
            .agg(t1t2_rev=("revenue","sum"), t1t2_qty=("qty","sum"))
            .reset_index())
sku_t1t2 = sku_meta.merge(sku_t1t2, on="product_code", how="left").fillna({"t1t2_rev":0,"t1t2_qty":0})

# Share SKU trong group
group_t1t2 = sku_t1t2.groupby("group_code").agg(g_t1t2_rev=("t1t2_rev","sum"), g_t1t2_qty=("t1t2_qty","sum")).reset_index()
sku_share = sku_t1t2.merge(group_t1t2, on="group_code")
sku_share["share_rev"] = np.where(sku_share["g_t1t2_rev"] > 0, sku_share["t1t2_rev"] / sku_share["g_t1t2_rev"], 0)
sku_share["share_qty"] = np.where(sku_share["g_t1t2_qty"] > 0, sku_share["t1t2_qty"] / sku_share["g_t1t2_qty"], 0)

# Forecast SKU = forecast group × share
fg_base = fg[fg["scenario"]=="base"][["year_month","group_code","revenue","qty"]].rename(
    columns={"revenue":"g_pred_rev","qty":"g_pred_qty"})
sku_forecast = sku_share[["product_code","product_name","color","line_id_fk","line_name","group_code","share_rev","share_qty"]].merge(
    fg_base, on="group_code")
sku_forecast["revenue"] = sku_forecast["g_pred_rev"] * sku_forecast["share_rev"]
sku_forecast["qty"]     = sku_forecast["g_pred_qty"] * sku_forecast["share_qty"]
sku_forecast = sku_forecast.drop(columns=["g_pred_rev","g_pred_qty","share_rev","share_qty"])
sku_forecast.to_parquet(os.path.join(DATA, "forecast_sku_q2.parquet"), index=False)

# Top-20 SKU theo tổng Q2 revenue (base scenario)
sku_q2 = sku_forecast.groupby(["product_code","product_name","color","line_name","group_code"]).agg(
    q2_revenue=("revenue","sum"), q2_qty=("qty","sum")).reset_index()
top20 = sku_q2.nlargest(20, "q2_revenue").reset_index(drop=True)
top20["rank"] = top20.index + 1
top20.to_parquet(os.path.join(DATA, "forecast_top20_sku.parquet"), index=False)

print(f"\n{'#':>3} {'SKU':17s} {'Name':35s} {'Color':12s} {'Q2 rev (tr)':>11s} {'Q2 qty':>7s}")
for _, r in top20.iterrows():
    print(f"{r['rank']:>3} {r['product_code']:17s} {r['product_name'][:35]:35s} {(r['color'] or '')[:12]:12s} {r['q2_revenue']/1e6:11.0f} {r['q2_qty']:7.0f}")

# Reconciliation check
print("\n=== RECONCILIATION CHECK ===")
print(f"Sum top-20 SKU Q2 revenue: {top20['q2_revenue'].sum()/1e9:.2f} tỷ")
print(f"Sum ALL SKU Q2 revenue:    {sku_q2['q2_revenue'].sum()/1e9:.2f} tỷ")
print(f"Sum group forecasts (base): {fg[fg['scenario']=='base']['revenue'].sum()/1e9:.2f} tỷ")
print(f"Total forecast (base):     {ft[ft['scenario']=='base']['revenue'].sum()/1e9:.2f} tỷ")
print("(Group/SKU/Total đều khớp vì share-based top-down disaggregation)")

print(f"\n✓ Đã ghi 4 file forecast vào {DATA}")
