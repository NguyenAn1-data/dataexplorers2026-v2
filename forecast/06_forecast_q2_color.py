"""
Phase C - Câu hỏi 2: Màu sắc Q2/2026 + SKU bán chậm

C.2.1 — Màu sắc nào sẽ tăng nhu cầu theo mùa
       So sánh share màu Q1/25 vs Q1/26 → trend dương / âm
       (KHÔNG có Q2 lịch sử nên không thể tính seasonal index Q2 cho màu)

C.2.2 — Tỷ trọng cơ cấu màu sắc dự kiến Q2/2026
       Aggregate SKU forecast Q2/26 theo color (trong từng group) → share

C.2.3 — SKU có dấu hiệu nhu cầu giảm / nguy cơ bán chậm
       Rule-based classifier:
       • Tiêu chí 1: T3/26 qty < 0.3 × avg(T1+T2/26) → giảm đột ngột
       • Tiêu chí 2: SKU active trong 2025 nhưng zero ở Q1/26 → đã chết
       • Tiêu chí 3: Q2/26 forecast revenue < 30% × Q1/26 actual revenue → suy giảm
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np

DATA = os.path.join(os.path.dirname(__file__), "data")

df_sku    = pd.read_parquet(os.path.join(DATA, "df_sku.parquet"))
df_color  = pd.read_parquet(os.path.join(DATA, "df_color.parquet"))
fcst_sku  = pd.read_parquet(os.path.join(DATA, "forecast_sku_q2.parquet"))

# ===============================================================
# C.2.1 — Color trend Q1/25 vs Q1/26
# ===============================================================
print("=" * 80)
print("C.2.1 — Màu sắc tăng/giảm nhu cầu (so Q1/25 vs Q1/26)")
print("=" * 80)

Q1_2025 = ["2025-01","2025-02","2025-03"]
Q1_2026 = ["2026-01","2026-02","2026-03"]

col_25 = df_color[df_color["year_month"].isin(Q1_2025)].groupby("color").agg(rev_25=("revenue","sum"), qty_25=("qty","sum")).reset_index()
col_26 = df_color[df_color["year_month"].isin(Q1_2026)].groupby("color").agg(rev_26=("revenue","sum"), qty_26=("qty","sum")).reset_index()
trend = col_25.merge(col_26, on="color", how="outer").fillna(0)

# Share = revenue / total revenue
tot_25 = trend["rev_25"].sum()
tot_26 = trend["rev_26"].sum()
trend["share_25"] = trend["rev_25"] / tot_25 * 100
trend["share_26"] = trend["rev_26"] / tot_26 * 100
trend["share_delta"] = trend["share_26"] - trend["share_25"]
trend = trend[trend["color"].notna()]
trend = trend.sort_values("share_26", ascending=False)

print(f"\n{'Color':18s} {'Share Q1/25':>11s} {'Share Q1/26':>11s} {'Δ share (pp)':>13s} {'Trend':>8s}")
for _, r in trend.head(15).iterrows():
    arrow = "↑↑" if r["share_delta"] > 1 else "↑" if r["share_delta"] > 0.2 else "↓↓" if r["share_delta"] < -1 else "↓" if r["share_delta"] < -0.2 else "≈"
    print(f"{r['color'][:18]:18s} {r['share_25']:11.2f} {r['share_26']:11.2f} {r['share_delta']:+13.2f} {arrow:>8s}")

trend.to_parquet(os.path.join(DATA, "color_trend.parquet"), index=False)

# Top trending colors
trending_up = trend[trend["share_delta"] > 0.5].nlargest(5, "share_delta")
trending_down = trend[trend["share_delta"] < -0.5].nsmallest(5, "share_delta")
print(f"\n→ Màu tăng share mạnh nhất Q1/26 vs Q1/25: {', '.join(trending_up['color'].tolist())}")
print(f"→ Màu giảm share mạnh nhất Q1/26 vs Q1/25: {', '.join(trending_down['color'].tolist())}")

# ===============================================================
# C.2.2 — Forecast share màu Q2/2026 theo group
# ===============================================================
print("\n" + "=" * 80)
print("C.2.2 — Tỷ trọng màu Q2/2026 (forecast, theo group)")
print("=" * 80)

# Aggregate Q2 SKU forecast theo (group, color)
q2_color = fcst_sku.groupby(["group_code","color"]).agg(q2_revenue=("revenue","sum"), q2_qty=("qty","sum")).reset_index()
q2_color["color"] = q2_color["color"].fillna("NA")
q2_color_group_tot = q2_color.groupby("group_code")["q2_revenue"].sum().reset_index().rename(columns={"q2_revenue":"g_total"})
q2_color = q2_color.merge(q2_color_group_tot, on="group_code")
q2_color["share_pct"] = q2_color["q2_revenue"] / q2_color["g_total"] * 100
q2_color = q2_color.sort_values(["group_code","share_pct"], ascending=[True, False])

for gc, sub in q2_color.groupby("group_code"):
    print(f"\n[{gc}] Q2/26 forecast revenue tổng = {sub['g_total'].iloc[0]/1e9:.2f} tỷ")
    top5 = sub.head(5)
    for _, r in top5.iterrows():
        print(f"   {r['color'][:18]:18s} {r['q2_revenue']/1e6:>7.0f} tr  ({r['share_pct']:5.2f}%)")

q2_color.to_parquet(os.path.join(DATA, "forecast_color_q2.parquet"), index=False)

# ===============================================================
# C.2.3 — Slow-mover SKUs
# ===============================================================
print("\n" + "=" * 80)
print("C.2.3 — SKU có dấu hiệu bán chậm / nguy cơ giảm Q2/2026")
print("=" * 80)

# Build per-SKU metrics
sku_meta = df_sku.groupby(["product_code","product_name","color","line_name","group_code"]).first().reset_index()[
    ["product_code","product_name","color","line_name","group_code"]]

# Q1/2026 actual revenue & qty
q1_26_sku = df_sku[df_sku["year_month"].isin(Q1_2026)].groupby("product_code").agg(
    q1_26_rev=("revenue","sum"), q1_26_qty=("qty","sum")).reset_index()

# T3/2026 vs avg(T1,T2)/26
t12_qty = df_sku[df_sku["year_month"].isin(["2026-01","2026-02"])].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"t12_qty"})
t3_qty  = df_sku[df_sku["year_month"]=="2026-03"].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"t3_qty"})

# 2025 activity check
y25_qty = df_sku[df_sku["year_month"].isin(Q1_2025)].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"q1_25_qty"})

# Q2/2026 forecast
q2_pred = fcst_sku.groupby("product_code").agg(q2_pred_rev=("revenue","sum"), q2_pred_qty=("qty","sum")).reset_index()

# Merge all
slow = sku_meta.merge(q1_26_sku, on="product_code", how="left") \
               .merge(t12_qty, on="product_code", how="left") \
               .merge(t3_qty, on="product_code", how="left") \
               .merge(y25_qty, on="product_code", how="left") \
               .merge(q2_pred, on="product_code", how="left")
slow = slow.fillna(0)

# Tiêu chí:
slow["t3_drop"]      = (slow["t12_qty"] >= 4) & (slow["t3_qty"] < 0.3 * (slow["t12_qty"]/2))   # T3 giảm > 70% so avg T1T2
slow["dead_in_2026"] = (slow["q1_25_qty"] >= 5) & (slow["q1_26_qty"] == 0)                    # active 25, zero 26
slow["pred_drop"]    = (slow["q1_26_rev"] > 0) & (slow["q2_pred_rev"] < 0.3 * (slow["q1_26_rev"]/3))  # Q2_pred/tháng < 30% Q1/26/tháng

slow["slow_mover"] = slow["t3_drop"] | slow["dead_in_2026"] | slow["pred_drop"]
slow["reasons"] = slow.apply(
    lambda r: "|".join([t for t,v in [
        ("T3_drop", r["t3_drop"]), ("dead_2026", r["dead_in_2026"]), ("pred_drop", r["pred_drop"])
    ] if v]) or "ok", axis=1)

# Filter
slow_only = slow[slow["slow_mover"]].copy()
print(f"\nTổng SKU: {len(slow):,}")
print(f"SKU bán chậm/nguy cơ: {len(slow_only):,}")
print(f"  - T3_drop (giảm >70% T3):     {slow['t3_drop'].sum():,}")
print(f"  - dead_in_2026:                {slow['dead_in_2026'].sum():,}")
print(f"  - pred_drop (Q2 dự báo giảm):  {slow['pred_drop'].sum():,}")

# Display top slow-movers by Q1/26 revenue (highest-impact)
high_impact = slow_only.nlargest(20, "q1_26_rev")
print(f"\nTop-20 SKU bán chậm (theo doanh thu Q1/26 — tác động lớn nhất nếu mất):")
print(f"{'SKU':17s} {'Name':35s} {'Q1/26 rev':>10s} {'Q2 pred':>9s} {'Reasons':25s}")
for _, r in high_impact.iterrows():
    print(f"{r['product_code']:17s} {r['product_name'][:35]:35s} {r['q1_26_rev']/1e6:10.0f} {r['q2_pred_rev']/1e6:9.0f} {r['reasons']:25s}")

slow.to_parquet(os.path.join(DATA, "forecast_slow_sku.parquet"), index=False)
print(f"\n✓ Đã ghi color_trend, forecast_color_q2, forecast_slow_sku vào {DATA}")
