"""
Backtest reconciliation: cải thiện SKU-level forecast bằng cách:
  M10 — Top-down: pred_sku = pred_group_M5 × (share SKU trong group dùng (T1+T2)/26)
  M11 — Hybrid 50/50: avg(M5 per-SKU, M10 top-down)
  M12 — Shrinkage seasonal idx: shrink seasonal_idx_sku về phía seasonal_idx_group
         theo Stein credibility, w = n_obs / (n_obs + k); SKU dataset nhỏ → trọng số nhỏ.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np

DATA = os.path.join(os.path.dirname(__file__), "data")

df_sku   = pd.read_parquet(os.path.join(DATA, "df_sku.parquet"))
df_group = pd.read_parquet(os.path.join(DATA, "df_group.parquet"))
sku_back = pd.read_parquet(os.path.join(DATA, "backtest_sku.parquet"))  # có pred_m5, pred_lgb
TARGET = "revenue"
ALL_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02","2026-03"]
TEST = "2026-03"

def wape(a, p):
    a = np.array(a, dtype=float); p = np.array(p, dtype=float)
    s = np.abs(a).sum()
    return float(np.abs(a-p).sum() / s) if s > 0 else np.nan

# ----- M5 group predictions -----
group_pivot = df_group.pivot(index="group_code", columns="year_month", values=TARGET).fillna(0)
group_m5 = {}
for gc, row in group_pivot.iterrows():
    q1_25_mean = (row.get("2025-01",0) + row.get("2025-02",0) + row.get("2025-03",0)) / 3
    avg12_26 = (row.get("2026-01",0) + row.get("2026-02",0)) / 2
    group_m5[gc] = avg12_26 * (row.get("2025-03",0) / q1_25_mean) if q1_25_mean > 0 else 0

# ----- SKU share within group dùng (T1+T2)/2026 -----
sku_meta = df_sku.groupby("product_code").agg({"group_code":"first"}).reset_index()
sku_panel = (sku_meta.merge(pd.DataFrame({"year_month": ALL_MONTHS}), how="cross")
                     .merge(df_sku[["product_code","year_month",TARGET]],
                            on=["product_code","year_month"], how="left").fillna({TARGET:0.0}))

def t1t2_2026(sub):
    d = dict(zip(sub["year_month"], sub[TARGET]))
    return d.get("2026-01",0) + d.get("2026-02",0)

sku_panel_grp = sku_panel.groupby(["product_code","group_code"]).apply(
    lambda s: pd.Series({"t1t2_26": t1t2_2026(s)})).reset_index()

# Group total of (T1+T2)/26
grp_t1t2 = sku_panel_grp.groupby("group_code")["t1t2_26"].sum().to_dict()

# Share
sku_panel_grp["share_t1t2"] = sku_panel_grp.apply(
    lambda r: r["t1t2_26"] / grp_t1t2[r["group_code"]] if grp_t1t2[r["group_code"]] > 0 else 0, axis=1)

# M10 prediction: pred = group_M5 × share
sku_panel_grp["pred_m10"] = sku_panel_grp.apply(
    lambda r: group_m5.get(r["group_code"], 0) * r["share_t1t2"], axis=1)

# ----- Merge với M5 và actual -----
res = sku_back[["product_code","target","pred_m5","pred_lgb"]].merge(
    sku_panel_grp[["product_code","group_code","pred_m10","share_t1t2"]], on="product_code")

# M11: hybrid 50/50
res["pred_m11"] = (res["pred_m5"] + res["pred_m10"]) / 2

# ----- M12: shrinkage seasonal idx -----
# Cho mỗi SKU: seasonal_idx_sku = T3/25 / Q1/25_mean (nếu có)
# Group seasonal_idx = T3/25_group / Q1/25_group_mean
# n_obs = số tháng trong Q1/25 mà SKU có doanh thu (max 3)
# Shrinkage k = 4: weight w = n / (n + k); idx_shrunk = w*idx_sku + (1-w)*idx_group
# Sau đó: pred = avg12_26_sku × idx_shrunk

group_seasonal_idx = {}
for gc, row in group_pivot.iterrows():
    q1_25_mean = (row.get("2025-01",0) + row.get("2025-02",0) + row.get("2025-03",0)) / 3
    group_seasonal_idx[gc] = row.get("2025-03",0) / q1_25_mean if q1_25_mean > 0 else 1.5

# Build per-SKU stats từ panel
panel_w = sku_panel.merge(sku_meta[["product_code","group_code"]], on="product_code", how="left", suffixes=("","_x"))
shrink_rows = []
K = 4.0
for (pc, gc), sub in panel_w.groupby(["product_code","group_code"]):
    d = dict(zip(sub["year_month"], sub[TARGET]))
    t1_25 = d.get("2025-01",0); t2_25 = d.get("2025-02",0); t3_25 = d.get("2025-03",0)
    t1_26 = d.get("2026-01",0); t2_26 = d.get("2026-02",0)
    n_obs = sum(v > 0 for v in [t1_25, t2_25, t3_25])
    q1_25_mean = (t1_25+t2_25+t3_25)/3 if (t1_25+t2_25+t3_25) > 0 else 0
    idx_sku = t3_25 / q1_25_mean if q1_25_mean > 0 else np.nan
    idx_group = group_seasonal_idx.get(gc, 1.5)
    w = n_obs / (n_obs + K)
    idx_shrunk = w * idx_sku + (1 - w) * idx_group if not np.isnan(idx_sku) else idx_group
    avg12_26 = (t1_26 + t2_26) / 2
    pred_m12 = avg12_26 * idx_shrunk
    shrink_rows.append({"product_code": pc, "pred_m12": pred_m12, "idx_shrunk": idx_shrunk, "n_obs": n_obs})

shrink = pd.DataFrame(shrink_rows)
res = res.merge(shrink[["product_code","pred_m12"]], on="product_code")

# ----- Đánh giá -----
print("=" * 80)
print("SKU-LEVEL BACKTEST — WAPE comparison")
print("=" * 80)
mask_nz = res["target"] > 0
for col, label in [("pred_m5","M5 per-SKU"), ("pred_lgb","M9 LightGBM"),
                   ("pred_m10","M10 Top-down"), ("pred_m11","M11 Hybrid 50/50"),
                   ("pred_m12","M12 Shrunk idx")]:
    w_all = wape(res["target"], res[col])
    w_nz  = wape(res.loc[mask_nz,"target"], res.loc[mask_nz,col])
    print(f"  {label:20s} WAPE_all = {w_all*100:5.1f}%  WAPE_nz = {w_nz*100:5.1f}%")

# Top-20 actual
top20 = res.nlargest(20, "target")
print(f"\nTop-20 SKU WAPE:")
for col, label in [("pred_m5","M5"), ("pred_m10","M10 Top-down"),
                   ("pred_m11","M11 Hybrid"), ("pred_m12","M12 Shrunk idx")]:
    print(f"  {label:20s} WAPE = {wape(top20['target'], top20[col])*100:5.1f}%")

# Group rollup từ mỗi method
agg = res.groupby("group_code").agg(actual=("target","sum"),
    m5=("pred_m5","sum"), m10=("pred_m10","sum"), m11=("pred_m11","sum"), m12=("pred_m12","sum")).reset_index()
agg["m5_err%"] = (agg["m5"]-agg["actual"])/agg["actual"]*100
agg["m10_err%"] = (agg["m10"]-agg["actual"])/agg["actual"]*100
agg["m11_err%"] = (agg["m11"]-agg["actual"])/agg["actual"]*100
agg["m12_err%"] = (agg["m12"]-agg["actual"])/agg["actual"]*100
print(f"\n=== Group rollup từ SKU predictions (revenue tỷ VND, err% so với actual) ===")
agg_display = agg.copy()
for c in ["actual","m5","m10","m11","m12"]:
    agg_display[c] = (agg_display[c]/1e9).round(2)
print(agg_display.to_string(index=False))

# Save
res.to_parquet(os.path.join(DATA, "backtest_sku_reconciled.parquet"), index=False)
print(f"\nSaved → {os.path.join(DATA, 'backtest_sku_reconciled.parquet')}")
