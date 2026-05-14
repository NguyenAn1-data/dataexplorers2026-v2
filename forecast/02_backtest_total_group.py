"""
Backtest tại 2 cấp: TOTAL + 5 GROUP
Train: T1/25, T2/25, T3/25, T1/26, T2/26
Holdout: T3/26 (đã biết, dùng làm ground truth)

Các phương pháp thử:
  M1  Naive last: dự đoán = T2/26
  M2  Naive avg2: dự đoán = avg(T1/26, T2/26)
  M3  YoY-T2: T3/26 = T3/25 × (T2/26 / T2/25)
  M4  YoY-avg: T3/26 = T3/25 × (avg(T1,T2)/26 / avg(T1,T2)/25)
  M5  Seasonal-multiplicative: T3/26 = avg(T1,T2)/26 × (T3/25 / mean(Q1/25))   ← chuẩn
  M6  Share-preservation: T3/26 = (T1+T2)/26 × share_T3_2025 / (1-share_T3_2025)
  M7  Damped YoY k=0.6: T3/26 = T3/25 × (YoY_avg)^0.6
  M8  Median ensemble (M2..M5)
  M9  LightGBM với features lag/group/calendar (global model toàn group)

Đo WAPE per method per level.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import warnings; warnings.filterwarnings("ignore")

import pandas as pd, numpy as np
import lightgbm as lgb

DATA = os.path.join(os.path.dirname(__file__), "data")

df_total = pd.read_parquet(os.path.join(DATA, "df_total.parquet"))
df_group = pd.read_parquet(os.path.join(DATA, "df_group.parquet"))

TARGET = "revenue"  # dùng doanh thu làm metric chính
TRAIN_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02"]
TEST_MONTH = "2026-03"

def wape(y_true, y_pred):
    y_true = np.array(y_true, dtype=float); y_pred = np.array(y_pred, dtype=float)
    s = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / s) if s > 0 else np.nan

def mape(y_true, y_pred):
    y_true = np.array(y_true, dtype=float); y_pred = np.array(y_pred, dtype=float)
    msk = y_true != 0
    return float(np.mean(np.abs((y_true[msk]-y_pred[msk]) / y_true[msk]))) if msk.any() else np.nan

# ----- methods on a single series (dict month -> value) -----
def predict_methods(s: dict):
    """s = {'2025-01': v, ..., '2026-02': v}. Trả về dict method->pred T3/26"""
    t1_25 = s.get("2025-01", 0.0)
    t2_25 = s.get("2025-02", 0.0)
    t3_25 = s.get("2025-03", 0.0)
    t1_26 = s.get("2026-01", 0.0)
    t2_26 = s.get("2026-02", 0.0)
    avg12_25 = (t1_25 + t2_25) / 2
    avg12_26 = (t1_26 + t2_26) / 2
    q1_25_sum = t1_25 + t2_25 + t3_25
    q1_25_mean = q1_25_sum / 3 if q1_25_sum > 0 else 1
    share_t3_25 = t3_25 / q1_25_sum if q1_25_sum > 0 else 0

    yoy_t2 = (t2_26 / t2_25) if t2_25 > 0 else np.nan
    yoy_avg = (avg12_26 / avg12_25) if avg12_25 > 0 else np.nan

    preds = {
        "M1_naive_last": t2_26,
        "M2_naive_avg2": avg12_26,
        "M3_yoy_t2":   t3_25 * yoy_t2 if not np.isnan(yoy_t2) else np.nan,
        "M4_yoy_avg":  t3_25 * yoy_avg if not np.isnan(yoy_avg) else np.nan,
        "M5_seasonal_mult": avg12_26 * (t3_25 / q1_25_mean) if q1_25_mean > 0 else np.nan,
        "M6_share_pres": (t1_26 + t2_26) * share_t3_25 / (1 - share_t3_25) if share_t3_25 < 1 else np.nan,
        "M7_damped_yoy": t3_25 * (yoy_avg ** 0.6) if not np.isnan(yoy_avg) and yoy_avg > 0 else np.nan,
    }
    # M8 = median of M2..M5
    candidates = [preds[k] for k in ("M2_naive_avg2","M3_yoy_t2","M4_yoy_avg","M5_seasonal_mult")]
    preds["M8_median_ens"] = float(np.nanmedian(candidates))
    return preds

def df_to_series(df, key_cols):
    """Convert long-form df with key_cols + year_month + TARGET → dict {key_tuple: {month: value}}"""
    out = {}
    for k, sub in df.groupby(key_cols):
        d = dict(zip(sub["year_month"], sub[TARGET]))
        out[k if isinstance(k, tuple) else (k,)] = d
    return out

# ======= TOTAL =======
print("=" * 80)
print("BACKTEST T3/2026 — TOTAL COMPANY (revenue, tỷ VND)")
print("=" * 80)
s_total = dict(zip(df_total["year_month"], df_total[TARGET]))
actual_total = s_total[TEST_MONTH]
preds_total = predict_methods({m: s_total[m] for m in TRAIN_MONTHS})
print(f"  Actual T3/26: {actual_total/1e9:.2f} tỷ\n")
rows = []
for method, p in preds_total.items():
    err = (p - actual_total) / actual_total
    print(f"  {method:25s}  pred={p/1e9:7.2f}  err={err*100:+6.1f}%")
    rows.append({"level":"total","series":"all","method":method,"pred":p,"actual":actual_total,"err_pct":err*100})

# ======= GROUP =======
print("\n" + "=" * 80)
print("BACKTEST T3/2026 — 5 PRODUCT GROUPS (revenue, tỷ VND)")
print("=" * 80)
group_series = df_to_series(df_group, ["group_code","group_name"])
all_method_preds = {}
for (gc, gn), s in sorted(group_series.items()):
    actual = s.get(TEST_MONTH, 0.0)
    preds = predict_methods({m: s.get(m, 0.0) for m in TRAIN_MONTHS})
    for method, p in preds.items():
        rows.append({"level":"group","series":gc,"method":method,"pred":p,"actual":actual,"err_pct":(p-actual)/actual*100 if actual else np.nan})
        all_method_preds.setdefault(method, []).append((gc, gn, actual, p))

print(f"\n{'Group':22s} {'Actual':>7s}  " + "  ".join(f"{m[:6]:>6s}" for m in preds_total.keys()))
for (gc, gn), s in sorted(group_series.items()):
    actual = s.get(TEST_MONTH, 0.0)
    preds = predict_methods({m: s.get(m, 0.0) for m in TRAIN_MONTHS})
    parts = [f"{p/1e9:6.2f}" for p in preds.values()]
    print(f"{gn[:22]:22s} {actual/1e9:7.2f}  " + "  ".join(parts))

print(f"\nWAPE per method across 5 groups:")
for method in preds_total.keys():
    actuals = [a for _, _, a, _ in all_method_preds[method]]
    pp      = [p for _, _, _, p in all_method_preds[method]]
    print(f"  {method:25s} WAPE = {wape(actuals, pp)*100:5.1f}%   MAPE = {mape(actuals, pp)*100:5.1f}%")

# ======= LightGBM M9 =======
print("\n" + "=" * 80)
print("BACKTEST T3/2026 — LightGBM (global model trên 5 groups)")
print("=" * 80)

def build_features(df, key, value):
    """Build (lag1, lag2, lag_yoy, mean_lag, month-cat, group-cat encoded) for each (key, month)."""
    df = df.sort_values([key, "year_month"]).copy()
    df["month_int"] = df["year_month"].str[-2:].astype(int)
    df["year_int"] = df["year_month"].str[:4].astype(int)
    rows = []
    for k, sub in df.groupby(key):
        sub = sub.reset_index(drop=True)
        for i, r in sub.iterrows():
            ym = r["year_month"]; m = r["month_int"]; y = r["year_int"]
            # lag1, lag2 from previous available months for this key
            prev = sub.iloc[:i]
            lag1 = prev[value].iloc[-1] if len(prev) >= 1 else np.nan
            lag2 = prev[value].iloc[-2] if len(prev) >= 2 else np.nan
            # YoY: same month previous year
            yoy_row = sub[(sub["year_int"] == y-1) & (sub["month_int"] == m)]
            lag_yoy = yoy_row[value].iloc[0] if len(yoy_row) else np.nan
            # YoY of prev month
            yoy_prev = sub[(sub["year_int"] == y-1) & (sub["month_int"] == m-1)] if m > 1 else pd.DataFrame()
            lag_yoy_prev = yoy_prev[value].iloc[0] if len(yoy_prev) else np.nan
            mean_lag = np.nanmean([lag1, lag2])
            rows.append({
                "key": k, "year_month": ym, "month": m, "year": y,
                "lag1": lag1, "lag2": lag2, "mean_lag": mean_lag,
                "lag_yoy": lag_yoy, "lag_yoy_prev": lag_yoy_prev,
                "target": r[value],
            })
    return pd.DataFrame(rows)

feat_g = build_features(df_group.rename(columns={"group_code":"_k"}).rename(columns={"_k":"group_code"}), "group_code", TARGET)
feat_g = feat_g.dropna(subset=["lag1"])  # cần ít nhất lag1

# Encode group key
feat_g["group_id"] = feat_g["key"].astype("category").cat.codes
feature_cols = ["lag1","lag2","mean_lag","lag_yoy","lag_yoy_prev","month","group_id"]

train_df = feat_g[feat_g["year_month"].isin(TRAIN_MONTHS)].copy()
test_df  = feat_g[feat_g["year_month"] == TEST_MONTH].copy()

print(f"  train rows: {len(train_df)}, test rows: {len(test_df)}")
print(f"  train months: {sorted(train_df['year_month'].unique())}")
print(f"  test months:  {sorted(test_df['year_month'].unique())}")

# LightGBM
params = dict(
    objective="regression",
    metric="mape",
    learning_rate=0.05,
    num_leaves=8,
    min_data_in_leaf=2,
    feature_fraction=0.9,
    bagging_fraction=0.9,
    bagging_freq=1,
    verbose=-1,
)
dtrain = lgb.Dataset(train_df[feature_cols], label=train_df["target"])
model = lgb.train(params, dtrain, num_boost_round=200)
test_df["pred"] = model.predict(test_df[feature_cols])

print(f"\n{'Group':22s} {'Actual':>8s} {'LGB pred':>10s}  Err")
for _, r in test_df.iterrows():
    err = (r["pred"]-r["target"])/r["target"]*100
    print(f"{r['key'][:22]:22s} {r['target']/1e9:7.2f} {r['pred']/1e9:10.2f}  {err:+6.1f}%")
    rows.append({"level":"group","series":r["key"],"method":"M9_lightgbm","pred":r["pred"],"actual":r["target"],"err_pct":err})

actuals = test_df["target"].tolist()
preds = test_df["pred"].tolist()
print(f"\n  LightGBM WAPE = {wape(actuals, preds)*100:.1f}%   MAPE = {mape(actuals, preds)*100:.1f}%")

# Save results
results = pd.DataFrame(rows)
results.to_parquet(os.path.join(DATA, "backtest_total_group.parquet"), index=False)
print(f"\nSaved → {os.path.join(DATA, 'backtest_total_group.parquet')}")
