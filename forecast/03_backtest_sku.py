"""
Backtest T3/2026 ở cấp SKU.
- M5 per-SKU + fallback xuống group level khi SKU thiếu lịch sử T3/25.
- LightGBM global toàn 265 SKU.
- So sánh WAPE trên (a) toàn bộ SKU có giao dịch T3/26, (b) top-20 SKU theo doanh thu T3/26.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np, lightgbm as lgb

DATA = os.path.join(os.path.dirname(__file__), "data")

df_sku = pd.read_parquet(os.path.join(DATA, "df_sku.parquet"))
df_group = pd.read_parquet(os.path.join(DATA, "df_group.parquet"))

TARGET = "revenue"
ALL_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02","2026-03"]
TRAIN_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02"]
TEST_MONTH = "2026-03"

# Tạo grid đầy đủ (SKU × all months) — fill 0 cho tháng không có giao dịch
sku_meta = df_sku.groupby("product_code").agg({
    "product_name":"first","color":"first","line_id_fk":"first","line_name":"first","group_code":"first"
}).reset_index()

grid = sku_meta[["product_code","group_code"]].merge(
    pd.DataFrame({"year_month": ALL_MONTHS}), how="cross")
panel = grid.merge(df_sku[["product_code","year_month",TARGET]],
                   on=["product_code","year_month"], how="left").fillna({TARGET: 0.0})

def wape(a, p):
    a = np.array(a, dtype=float); p = np.array(p, dtype=float)
    s = np.abs(a).sum()
    return float(np.abs(a-p).sum() / s) if s > 0 else np.nan

def seasonal_mult_predict(s):
    """M5: T3/26 = avg(T1,T2/26) × (T3/25 / mean(Q1/25))"""
    t1_25 = s.get("2025-01", 0.0); t2_25 = s.get("2025-02", 0.0); t3_25 = s.get("2025-03", 0.0)
    t1_26 = s.get("2026-01", 0.0); t2_26 = s.get("2026-02", 0.0)
    q1_25_mean = (t1_25 + t2_25 + t3_25) / 3
    avg12_26 = (t1_26 + t2_26) / 2
    if q1_25_mean <= 0:
        return np.nan
    return avg12_26 * (t3_25 / q1_25_mean)

# Tính group-level seasonal multiplier (scale factor cho fallback)
group_pivot = df_group.pivot(index="group_code", columns="year_month", values=TARGET).fillna(0)
group_factor = {}  # group_code → (T3/25 / mean(Q1/25))
for gc, row in group_pivot.iterrows():
    q1m = (row.get("2025-01",0) + row.get("2025-02",0) + row.get("2025-03",0)) / 3
    if q1m > 0:
        group_factor[gc] = row.get("2025-03",0) / q1m
    else:
        group_factor[gc] = 1.0

# ====== M5 per-SKU + fallback group ======
results = []
for pc, sub in panel.groupby("product_code"):
    gc = sub["group_code"].iloc[0]
    s = dict(zip(sub["year_month"], sub[TARGET]))
    actual = s[TEST_MONTH]
    pred_m5 = seasonal_mult_predict(s)
    if pd.isna(pred_m5):
        # Fallback: dùng group factor × avg(T1,T2)/26 của SKU
        avg12_26 = (s.get("2026-01",0) + s.get("2026-02",0)) / 2
        pred_m5 = avg12_26 * group_factor.get(gc, 1.0)
    results.append({"product_code": pc, "group_code": gc, "actual": actual, "pred_m5": pred_m5})

res = pd.DataFrame(results)

# Đếm coverage
nonzero_actual = res[res["actual"] > 0]
print(f"Total SKU: {len(res):,}  |  có doanh thu T3/26: {len(nonzero_actual):,}")
print(f"M5 SKU-level WAPE (toàn bộ):      {wape(res['actual'], res['pred_m5'])*100:.1f}%")
print(f"M5 SKU-level WAPE (chỉ SKU>0 T3): {wape(nonzero_actual['actual'], nonzero_actual['pred_m5'])*100:.1f}%")

# Top 20 SKU theo actual T3/26
top20 = nonzero_actual.nlargest(20, "actual").copy()
top20["err_pct"] = (top20["pred_m5"] - top20["actual"]) / top20["actual"] * 100
top20_meta = top20.merge(sku_meta[["product_code","product_name"]], on="product_code")
print(f"\n=== TOP-20 SKU (actual T3/26) — M5 prediction (revenue triệu VND) ===")
print(f"{'SKU':17s} {'Name':35s} {'Actual':>8s} {'Pred':>8s}  Err")
for _, r in top20_meta.iterrows():
    name = r["product_name"][:35]
    print(f"{r['product_code']:17s} {name:35s} {r['actual']/1e6:8.0f} {r['pred_m5']/1e6:8.0f}  {r['err_pct']:+6.1f}%")
print(f"\nTop-20 WAPE: {wape(top20['actual'], top20['pred_m5'])*100:.1f}%")

# ====== LightGBM SKU global ======
print("\n" + "="*80)
print("LightGBM SKU global model")
print("="*80)

# Build features: lag_1, lag_2, lag_yoy (same month last year), group encoding, line, color
# Train pairs: (sku, target_month=2025-02..2026-02) → target=value, features from prior months/yoy.
months_idx = {m:i for i,m in enumerate(ALL_MONTHS)}

def build_features(panel_df, train_months, test_month):
    panel_df = panel_df.merge(sku_meta[["product_code","color","line_id_fk","group_code"]],
                              on=["product_code","group_code"], how="left")
    rows = []
    panel_idx = panel_df.set_index(["product_code","year_month"]).to_dict()[TARGET]
    for (pc, gc, color, line_id), sub in panel_df.groupby(["product_code","group_code","color","line_id_fk"]):
        d = dict(zip(sub["year_month"], sub[TARGET]))
        for ym in ALL_MONTHS:
            if ym not in train_months and ym != test_month:
                continue
            yr = int(ym[:4]); m = int(ym[-2:])
            # previous calendar month in our sparse panel: just look at preceding ym in ALL_MONTHS
            i = months_idx[ym]
            lag1 = d[ALL_MONTHS[i-1]] if i >= 1 else np.nan
            lag2 = d[ALL_MONTHS[i-2]] if i >= 2 else np.nan
            yoy_ym = f"{yr-1}-{m:02d}"
            lag_yoy = d.get(yoy_ym, np.nan)
            # group-level YoY (more stable signal)
            g_d = group_pivot.loc[gc].to_dict() if gc in group_pivot.index else {}
            g_lag1 = g_d.get(ALL_MONTHS[i-1], np.nan) if i >= 1 else np.nan
            g_yoy = g_d.get(yoy_ym, np.nan)
            rows.append({
                "product_code": pc, "year_month": ym,
                "group_code": gc, "color": str(color) if color else "NA", "line_id": int(line_id) if line_id else 0,
                "month": m,
                "lag1": lag1, "lag2": lag2, "lag_yoy": lag_yoy,
                "g_lag1": g_lag1, "g_yoy": g_yoy,
                "ratio_yoy_g": (g_lag1/g_yoy) if (g_yoy and g_yoy>0) else np.nan,
                "target": d[ym],
            })
    return pd.DataFrame(rows)

feat = build_features(panel, TRAIN_MONTHS, TEST_MONTH)
# Encode categorical
feat["group_id"] = feat["group_code"].astype("category").cat.codes
feat["color_id"] = feat["color"].astype("category").cat.codes
feat["line_int"] = feat["line_id"].astype(int)

feat_cols = ["lag1","lag2","lag_yoy","g_lag1","g_yoy","ratio_yoy_g","month","group_id","color_id","line_int"]

train_df = feat[feat["year_month"].isin(TRAIN_MONTHS)].copy()
test_df  = feat[feat["year_month"] == TEST_MONTH].copy()
# Drop rows where target=0 AND lag1=0 from train (no signal)
train_df = train_df[~((train_df["target"]==0) & (train_df["lag1"].fillna(0)==0))]

print(f"  train rows: {len(train_df):,}  test rows: {len(test_df):,}")

params = dict(objective="regression_l1", metric="mape", learning_rate=0.05,
              num_leaves=31, min_data_in_leaf=10, feature_fraction=0.85,
              bagging_fraction=0.85, bagging_freq=1, verbose=-1)
dtrain = lgb.Dataset(train_df[feat_cols], label=train_df["target"])
model = lgb.train(params, dtrain, num_boost_round=400)
test_df["pred_lgb"] = model.predict(test_df[feat_cols])
test_df["pred_lgb"] = test_df["pred_lgb"].clip(lower=0)

merged = test_df[["product_code","target","pred_lgb"]].merge(res[["product_code","pred_m5"]], on="product_code")
print(f"\nLightGBM SKU WAPE (toàn bộ):      {wape(merged['target'], merged['pred_lgb'])*100:.1f}%")
print(f"LightGBM SKU WAPE (SKU>0 T3):     {wape(merged[merged['target']>0]['target'], merged[merged['target']>0]['pred_lgb'])*100:.1f}%")

# Ensemble: M5 + LightGBM (simple average)
merged["pred_ens"] = (merged["pred_m5"] + merged["pred_lgb"]) / 2
print(f"Ensemble WAPE (toàn bộ):          {wape(merged['target'], merged['pred_ens'])*100:.1f}%")
print(f"Ensemble WAPE (SKU>0 T3):         {wape(merged[merged['target']>0]['target'], merged[merged['target']>0]['pred_ens'])*100:.1f}%")

# Đối với top-20 actual
m_top20 = merged[merged["product_code"].isin(top20["product_code"])]
print(f"\nTop-20 SKU comparison:")
print(f"  M5         WAPE: {wape(m_top20['target'], m_top20['pred_m5'])*100:.1f}%")
print(f"  LightGBM   WAPE: {wape(m_top20['target'], m_top20['pred_lgb'])*100:.1f}%")
print(f"  Ensemble   WAPE: {wape(m_top20['target'], m_top20['pred_ens'])*100:.1f}%")

# Save
merged.to_parquet(os.path.join(DATA, "backtest_sku.parquet"), index=False)
print(f"\nSaved → {os.path.join(DATA, 'backtest_sku.parquet')}")

# Aggregate SKU predictions back to group → check group-level WAPE
sku_to_group = sku_meta[["product_code","group_code"]]
agg = merged.merge(sku_to_group, on="product_code").groupby("group_code").agg(
    actual=("target","sum"), pred_m5=("pred_m5","sum"), pred_lgb=("pred_lgb","sum"), pred_ens=("pred_ens","sum")
).reset_index()
print(f"\n=== Aggregate SKU→Group reconciliation check ===")
print(agg.to_string(index=False))
print(f"\nGroup-from-SKU WAPE: M5={wape(agg['actual'], agg['pred_m5'])*100:.1f}%  LGB={wape(agg['actual'], agg['pred_lgb'])*100:.1f}%  Ens={wape(agg['actual'], agg['pred_ens'])*100:.1f}%")
