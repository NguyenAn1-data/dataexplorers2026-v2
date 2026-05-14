"""
pipeline_forecast.py — Gộp toàn bộ Phase C: từ build dataset → ghi forecast vào DB.

Chạy 1 lệnh:  python pipeline_forecast.py

Các bước (tương ứng file 01..08 gốc):
  1) build_dataset()             — đọc fact_sales → df_total/group/sku/color/dealer
  2) backtest_total_group()      — M1..M9 trên T3/26 (TOTAL + GROUP)
  3) backtest_sku()              — M5 + LightGBM ở cấp SKU
  4) backtest_reconciled()       — M10 top-down, M11 hybrid, M12 shrunk idx
  5) forecast_q2_sales()         — Q2/26 total/group/SKU + top-20
  6) forecast_q2_color()         — color trend + share Q2 + slow-movers
  7) dealer_forecast()           — BG/NBD + Gamma-Gamma → tier 798 đại lý
  8) write_forecasts_to_db()     — push 8 bảng vào schema tnbike_forecast
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import lightgbm as lgb
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data

# ─────────────────────────── CONFIG ───────────────────────────
CONN = dict(host="localhost", dbname="tnbike_db", user="postgres", password="123456")
DATA = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA, exist_ok=True)

TARGET = "revenue"
ALL_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02","2026-03"]
TRAIN_MONTHS = ["2025-01","2025-02","2025-03","2026-01","2026-02"]
TEST_MONTH = "2026-03"
MONTH_FACTORS = {"2026-04": 1.05, "2026-05": 1.07, "2026-06": 1.10}
SCENARIOS = {"pessimistic": 0.85, "base": 1.00, "optimistic": 1.15}
FORECAST_MONTHS = list(MONTH_FACTORS.keys())
Q1_2025 = ["2025-01","2025-02","2025-03"]
Q1_2026 = ["2026-01","2026-02","2026-03"]
OBS_END = "2026-03-31"

def _p(path): return os.path.join(DATA, path)
def wape(a, p):
    a = np.array(a, dtype=float); p = np.array(p, dtype=float)
    s = np.abs(a).sum()
    return float(np.abs(a - p).sum() / s) if s > 0 else np.nan
def mape(a, p):
    a = np.array(a, dtype=float); p = np.array(p, dtype=float)
    m = a != 0
    return float(np.mean(np.abs((a[m]-p[m])/a[m]))) if m.any() else np.nan

# ─────────────────────── 1. BUILD DATASET ───────────────────────
def build_dataset():
    print("\n[1/8] BUILD DATASET")
    conn = psycopg2.connect(**CONN)
    f = pd.read_sql("""
        SELECT fact_id, order_date, fiscal_year, fiscal_month,
               so_number, order_id, customer_code, province_id, region,
               product_code, product_name, color, line_id_fk, line_name, group_code, group_name,
               quantity::float AS quantity, unit_price::float AS unit_price, line_total::float AS line_total
        FROM tnbike.fact_sales
    """, conn)
    conn.close()
    f["order_date"] = pd.to_datetime(f["order_date"])
    f["year_month"] = f["order_date"].dt.to_period("M").astype(str)
    print(f"  fact rows: {len(f):,}  months: {sorted(f['year_month'].unique())}")

    df_total = (f.groupby("year_month")
                  .agg(qty=("quantity","sum"), revenue=("line_total","sum"),
                       orders=("so_number","nunique"), lines=("fact_id","count"),
                       active_dealers=("customer_code","nunique"),
                       active_skus=("product_code","nunique"))
                  .reset_index().sort_values("year_month"))
    df_group = (f.groupby(["year_month","group_code","group_name"])
                  .agg(qty=("quantity","sum"), revenue=("line_total","sum"),
                       orders=("so_number","nunique"), lines=("fact_id","count"))
                  .reset_index().sort_values(["group_code","year_month"]))
    df_sku = (f.groupby(["year_month","product_code","product_name","color",
                         "line_id_fk","line_name","group_code"])
                .agg(qty=("quantity","sum"), revenue=("line_total","sum"),
                     orders=("so_number","nunique"))
                .reset_index().sort_values(["product_code","year_month"]))
    df_color = (f.groupby(["year_month","group_code","color"])
                  .agg(qty=("quantity","sum"), revenue=("line_total","sum"))
                  .reset_index().sort_values(["group_code","color","year_month"]))
    df_dealer = (f.groupby(["customer_code","order_date","so_number"])
                   .agg(amount=("line_total","sum"), qty=("quantity","sum"))
                   .reset_index())

    for name, d in [("total",df_total),("group",df_group),("sku",df_sku),
                    ("color",df_color),("dealer_trans",df_dealer)]:
        d.to_parquet(_p(f"df_{name}.parquet"), index=False)
        print(f"  df_{name:14s} -> {len(d):>6,} rows")

# ─────────────────── 2. BACKTEST TOTAL + GROUP ───────────────────
def _predict_methods(s):
    t1_25, t2_25, t3_25 = s.get("2025-01",0.0), s.get("2025-02",0.0), s.get("2025-03",0.0)
    t1_26, t2_26 = s.get("2026-01",0.0), s.get("2026-02",0.0)
    avg12_25 = (t1_25 + t2_25)/2; avg12_26 = (t1_26 + t2_26)/2
    q1_25_sum = t1_25 + t2_25 + t3_25
    q1_25_mean = q1_25_sum/3 if q1_25_sum > 0 else 1
    share_t3_25 = t3_25/q1_25_sum if q1_25_sum > 0 else 0
    yoy_t2 = (t2_26/t2_25) if t2_25 > 0 else np.nan
    yoy_avg = (avg12_26/avg12_25) if avg12_25 > 0 else np.nan
    preds = {
        "M1_naive_last": t2_26,
        "M2_naive_avg2": avg12_26,
        "M3_yoy_t2":  t3_25 * yoy_t2 if not np.isnan(yoy_t2) else np.nan,
        "M4_yoy_avg": t3_25 * yoy_avg if not np.isnan(yoy_avg) else np.nan,
        "M5_seasonal_mult": avg12_26 * (t3_25/q1_25_mean) if q1_25_mean > 0 else np.nan,
        "M6_share_pres": (t1_26+t2_26)*share_t3_25/(1-share_t3_25) if share_t3_25 < 1 else np.nan,
        "M7_damped_yoy": t3_25*(yoy_avg**0.6) if not np.isnan(yoy_avg) and yoy_avg>0 else np.nan,
    }
    cands = [preds[k] for k in ("M2_naive_avg2","M3_yoy_t2","M4_yoy_avg","M5_seasonal_mult")]
    preds["M8_median_ens"] = float(np.nanmedian(cands))
    return preds

def backtest_total_group():
    print("\n[2/8] BACKTEST TOTAL + GROUP")
    df_total = pd.read_parquet(_p("df_total.parquet"))
    df_group = pd.read_parquet(_p("df_group.parquet"))
    rows = []

    s_total = dict(zip(df_total["year_month"], df_total[TARGET]))
    actual_total = s_total[TEST_MONTH]
    preds_total = _predict_methods({m: s_total[m] for m in TRAIN_MONTHS})
    print(f"  TOTAL Actual T3/26: {actual_total/1e9:.2f} tỷ")
    for method, p in preds_total.items():
        rows.append({"level":"total","series":"all","method":method,"pred":p,
                     "actual":actual_total,"err_pct":(p-actual_total)/actual_total*100})

    group_series = {}
    for (gc, gn), sub in df_group.groupby(["group_code","group_name"]):
        group_series[(gc,gn)] = dict(zip(sub["year_month"], sub[TARGET]))
    method_acc = {}
    for (gc, gn), s in group_series.items():
        actual = s.get(TEST_MONTH, 0.0)
        preds = _predict_methods({m: s.get(m,0.0) for m in TRAIN_MONTHS})
        for method, p in preds.items():
            rows.append({"level":"group","series":gc,"method":method,"pred":p,"actual":actual,
                         "err_pct":(p-actual)/actual*100 if actual else np.nan})
            method_acc.setdefault(method, []).append((actual, p))
    print("  WAPE per method (5 groups):")
    for method, vals in method_acc.items():
        a = [x[0] for x in vals]; pp = [x[1] for x in vals]
        print(f"    {method:25s} WAPE={wape(a,pp)*100:5.1f}%  MAPE={mape(a,pp)*100:5.1f}%")

    # M9 LightGBM
    df = df_group.sort_values(["group_code","year_month"]).copy()
    df["month_int"] = df["year_month"].str[-2:].astype(int)
    df["year_int"] = df["year_month"].str[:4].astype(int)
    fr = []
    for k, sub in df.groupby("group_code"):
        sub = sub.reset_index(drop=True)
        for i, r in sub.iterrows():
            prev = sub.iloc[:i]
            lag1 = prev[TARGET].iloc[-1] if len(prev)>=1 else np.nan
            lag2 = prev[TARGET].iloc[-2] if len(prev)>=2 else np.nan
            yoy = sub[(sub["year_int"]==r["year_int"]-1) & (sub["month_int"]==r["month_int"])]
            yoy_p = sub[(sub["year_int"]==r["year_int"]-1) & (sub["month_int"]==r["month_int"]-1)] if r["month_int"]>1 else pd.DataFrame()
            fr.append({"key":k,"year_month":r["year_month"],"month":r["month_int"],
                       "lag1":lag1,"lag2":lag2,"mean_lag":np.nanmean([lag1,lag2]),
                       "lag_yoy":yoy[TARGET].iloc[0] if len(yoy) else np.nan,
                       "lag_yoy_prev":yoy_p[TARGET].iloc[0] if len(yoy_p) else np.nan,
                       "target":r[TARGET]})
    feat = pd.DataFrame(fr).dropna(subset=["lag1"])
    feat["group_id"] = feat["key"].astype("category").cat.codes
    feat_cols = ["lag1","lag2","mean_lag","lag_yoy","lag_yoy_prev","month","group_id"]
    tr = feat[feat["year_month"].isin(TRAIN_MONTHS)]
    te = feat[feat["year_month"] == TEST_MONTH].copy()
    params = dict(objective="regression", metric="mape", learning_rate=0.05,
                  num_leaves=8, min_data_in_leaf=2, feature_fraction=0.9,
                  bagging_fraction=0.9, bagging_freq=1, verbose=-1)
    model = lgb.train(params, lgb.Dataset(tr[feat_cols], label=tr["target"]), num_boost_round=200)
    te["pred"] = model.predict(te[feat_cols])
    for _, r in te.iterrows():
        rows.append({"level":"group","series":r["key"],"method":"M9_lightgbm",
                     "pred":r["pred"],"actual":r["target"],
                     "err_pct":(r["pred"]-r["target"])/r["target"]*100})
    print(f"    M9_lightgbm              WAPE={wape(te['target'],te['pred'])*100:5.1f}%")
    pd.DataFrame(rows).to_parquet(_p("backtest_total_group.parquet"), index=False)

# ─────────────────────── 3. BACKTEST SKU ───────────────────────
def backtest_sku():
    print("\n[3/8] BACKTEST SKU")
    df_sku = pd.read_parquet(_p("df_sku.parquet"))
    df_group = pd.read_parquet(_p("df_group.parquet"))
    sku_meta = df_sku.groupby("product_code").agg({
        "product_name":"first","color":"first","line_id_fk":"first",
        "line_name":"first","group_code":"first"}).reset_index()

    grid = sku_meta[["product_code","group_code"]].merge(
        pd.DataFrame({"year_month": ALL_MONTHS}), how="cross")
    panel = grid.merge(df_sku[["product_code","year_month",TARGET]],
                       on=["product_code","year_month"], how="left").fillna({TARGET:0.0})

    group_pivot = df_group.pivot(index="group_code", columns="year_month", values=TARGET).fillna(0)
    group_factor = {}
    for gc, row in group_pivot.iterrows():
        q1m = (row.get("2025-01",0)+row.get("2025-02",0)+row.get("2025-03",0))/3
        group_factor[gc] = row.get("2025-03",0)/q1m if q1m > 0 else 1.0

    def m5_pred(s):
        t1_25,t2_25,t3_25 = s.get("2025-01",0),s.get("2025-02",0),s.get("2025-03",0)
        t1_26,t2_26 = s.get("2026-01",0),s.get("2026-02",0)
        q1m = (t1_25+t2_25+t3_25)/3
        if q1m <= 0: return np.nan
        return ((t1_26+t2_26)/2) * (t3_25/q1m)

    results = []
    for pc, sub in panel.groupby("product_code"):
        gc = sub["group_code"].iloc[0]
        s = dict(zip(sub["year_month"], sub[TARGET]))
        pred = m5_pred(s)
        if pd.isna(pred):
            pred = ((s.get("2026-01",0)+s.get("2026-02",0))/2) * group_factor.get(gc,1.0)
        results.append({"product_code":pc,"group_code":gc,"actual":s[TEST_MONTH],"pred_m5":pred})
    res = pd.DataFrame(results)
    nz = res[res["actual"] > 0]
    print(f"  Total SKU={len(res):,}  có rev T3/26={len(nz):,}")
    print(f"  M5 SKU WAPE all={wape(res['actual'],res['pred_m5'])*100:.1f}% nz={wape(nz['actual'],nz['pred_m5'])*100:.1f}%")

    # LightGBM SKU
    months_idx = {m:i for i,m in enumerate(ALL_MONTHS)}
    panel_x = panel.merge(sku_meta[["product_code","color","line_id_fk","group_code"]],
                          on=["product_code","group_code"], how="left")
    fr = []
    for (pc, gc, color, line_id), sub in panel_x.groupby(["product_code","group_code","color","line_id_fk"]):
        d = dict(zip(sub["year_month"], sub[TARGET]))
        for ym in ALL_MONTHS:
            if ym not in TRAIN_MONTHS and ym != TEST_MONTH: continue
            yr, m = int(ym[:4]), int(ym[-2:]); i = months_idx[ym]
            lag1 = d[ALL_MONTHS[i-1]] if i>=1 else np.nan
            lag2 = d[ALL_MONTHS[i-2]] if i>=2 else np.nan
            yoy_ym = f"{yr-1}-{m:02d}"
            g_d = group_pivot.loc[gc].to_dict() if gc in group_pivot.index else {}
            g_lag1 = g_d.get(ALL_MONTHS[i-1], np.nan) if i>=1 else np.nan
            g_yoy = g_d.get(yoy_ym, np.nan)
            fr.append({"product_code":pc,"year_month":ym,"group_code":gc,
                       "color":str(color) if color else "NA",
                       "line_id":int(line_id) if line_id else 0,"month":m,
                       "lag1":lag1,"lag2":lag2,"lag_yoy":d.get(yoy_ym,np.nan),
                       "g_lag1":g_lag1,"g_yoy":g_yoy,
                       "ratio_yoy_g":(g_lag1/g_yoy) if (g_yoy and g_yoy>0) else np.nan,
                       "target":d[ym]})
    feat = pd.DataFrame(fr)
    feat["group_id"] = feat["group_code"].astype("category").cat.codes
    feat["color_id"] = feat["color"].astype("category").cat.codes
    feat["line_int"] = feat["line_id"].astype(int)
    cols = ["lag1","lag2","lag_yoy","g_lag1","g_yoy","ratio_yoy_g","month","group_id","color_id","line_int"]
    tr = feat[feat["year_month"].isin(TRAIN_MONTHS)].copy()
    te = feat[feat["year_month"] == TEST_MONTH].copy()
    tr = tr[~((tr["target"]==0) & (tr["lag1"].fillna(0)==0))]
    params = dict(objective="regression_l1", metric="mape", learning_rate=0.05,
                  num_leaves=31, min_data_in_leaf=10, feature_fraction=0.85,
                  bagging_fraction=0.85, bagging_freq=1, verbose=-1)
    model = lgb.train(params, lgb.Dataset(tr[cols], label=tr["target"]), num_boost_round=400)
    te["pred_lgb"] = model.predict(te[cols]).clip(min=0)
    merged = te[["product_code","target","pred_lgb"]].merge(res[["product_code","pred_m5"]], on="product_code")
    merged["pred_ens"] = (merged["pred_m5"] + merged["pred_lgb"]) / 2
    print(f"  LGB SKU WAPE all={wape(merged['target'],merged['pred_lgb'])*100:.1f}%  Ens={wape(merged['target'],merged['pred_ens'])*100:.1f}%")
    merged.to_parquet(_p("backtest_sku.parquet"), index=False)

# ─────────────────── 4. BACKTEST RECONCILED ───────────────────
def backtest_reconciled():
    print("\n[4/8] BACKTEST RECONCILED (M10/M11/M12)")
    df_sku = pd.read_parquet(_p("df_sku.parquet"))
    df_group = pd.read_parquet(_p("df_group.parquet"))
    sku_back = pd.read_parquet(_p("backtest_sku.parquet"))

    group_pivot = df_group.pivot(index="group_code", columns="year_month", values=TARGET).fillna(0)
    group_m5 = {}
    group_idx = {}
    for gc, row in group_pivot.iterrows():
        q1m = (row.get("2025-01",0)+row.get("2025-02",0)+row.get("2025-03",0))/3
        avg12 = (row.get("2026-01",0)+row.get("2026-02",0))/2
        group_m5[gc] = avg12*(row.get("2025-03",0)/q1m) if q1m>0 else 0
        group_idx[gc] = row.get("2025-03",0)/q1m if q1m>0 else 1.5

    sku_meta = df_sku.groupby("product_code").agg({"group_code":"first"}).reset_index()
    sku_panel = (sku_meta.merge(pd.DataFrame({"year_month": ALL_MONTHS}), how="cross")
                          .merge(df_sku[["product_code","year_month",TARGET]],
                                 on=["product_code","year_month"], how="left").fillna({TARGET:0.0}))

    t1t2 = (sku_panel[sku_panel["year_month"].isin(["2026-01","2026-02"])]
            .groupby(["product_code","group_code"])[TARGET].sum().reset_index()
            .rename(columns={TARGET:"t1t2_26"}))
    grp_t1t2 = t1t2.groupby("group_code")["t1t2_26"].sum().to_dict()
    t1t2["share_t1t2"] = t1t2.apply(
        lambda r: r["t1t2_26"]/grp_t1t2[r["group_code"]] if grp_t1t2[r["group_code"]]>0 else 0, axis=1)
    t1t2["pred_m10"] = t1t2.apply(lambda r: group_m5.get(r["group_code"],0)*r["share_t1t2"], axis=1)

    res = sku_back[["product_code","target","pred_m5","pred_lgb"]].merge(
        t1t2[["product_code","group_code","pred_m10","share_t1t2"]], on="product_code")
    res["pred_m11"] = (res["pred_m5"] + res["pred_m10"]) / 2

    K = 4.0
    shrink = []
    for (pc, gc), sub in sku_panel.groupby(["product_code","group_code"]):
        d = dict(zip(sub["year_month"], sub[TARGET]))
        t1_25,t2_25,t3_25 = d.get("2025-01",0),d.get("2025-02",0),d.get("2025-03",0)
        t1_26,t2_26 = d.get("2026-01",0),d.get("2026-02",0)
        n_obs = sum(v>0 for v in [t1_25,t2_25,t3_25])
        q1m = (t1_25+t2_25+t3_25)/3 if (t1_25+t2_25+t3_25)>0 else 0
        idx_sku = t3_25/q1m if q1m>0 else np.nan
        idx_g = group_idx.get(gc, 1.5)
        w = n_obs/(n_obs+K)
        idx_sh = w*idx_sku + (1-w)*idx_g if not np.isnan(idx_sku) else idx_g
        shrink.append({"product_code":pc, "pred_m12": ((t1_26+t2_26)/2)*idx_sh})
    res = res.merge(pd.DataFrame(shrink), on="product_code")

    mask_nz = res["target"] > 0
    for col, label in [("pred_m5","M5"),("pred_lgb","M9_LGB"),("pred_m10","M10_TD"),
                       ("pred_m11","M11_Hybrid"),("pred_m12","M12_Shrunk")]:
        print(f"  {label:12s} WAPE_all={wape(res['target'],res[col])*100:5.1f}%  WAPE_nz={wape(res.loc[mask_nz,'target'],res.loc[mask_nz,col])*100:5.1f}%")
    res.to_parquet(_p("backtest_sku_reconciled.parquet"), index=False)

# ───────────────────── 5. FORECAST Q2 SALES ─────────────────────
def forecast_q2_sales():
    print("\n[5/8] FORECAST Q2/2026 SALES")
    df_total = pd.read_parquet(_p("df_total.parquet"))
    df_group = pd.read_parquet(_p("df_group.parquet"))
    df_sku   = pd.read_parquet(_p("df_sku.parquet"))

    def baseline(s): return (s.get("2026-01",0) + s.get("2026-02",0)) / 2

    s_rev = dict(zip(df_total["year_month"], df_total["revenue"]))
    s_qty = dict(zip(df_total["year_month"], df_total["qty"]))
    s_ord = dict(zip(df_total["year_month"], df_total["orders"]))
    br, bq, bo = baseline(s_rev), baseline(s_qty), baseline(s_ord)
    rows = []
    for m, mf in MONTH_FACTORS.items():
        for scn, sf in SCENARIOS.items():
            rows.append({"year_month":m,"scenario":scn,
                         "revenue":br*mf*sf,"qty":bq*mf*sf,"orders":bo*mf*sf,
                         "month_factor":mf,"scenario_factor":sf})
    ft = pd.DataFrame(rows); ft.to_parquet(_p("forecast_total_q2.parquet"), index=False)
    print(f"  Q2 BASE total revenue: {ft[ft['scenario']=='base']['revenue'].sum()/1e9:.2f} tỷ")

    rows = []
    for (gc, gn), sub in df_group.groupby(["group_code","group_name"]):
        sr = dict(zip(sub["year_month"], sub["revenue"]))
        sq = dict(zip(sub["year_month"], sub["qty"]))
        br_, bq_ = baseline(sr), baseline(sq)
        for m, mf in MONTH_FACTORS.items():
            for scn, sf in SCENARIOS.items():
                rows.append({"year_month":m,"group_code":gc,"group_name":gn,"scenario":scn,
                             "revenue":br_*mf*sf,"qty":bq_*mf*sf})
    fg = pd.DataFrame(rows); fg.to_parquet(_p("forecast_group_q2.parquet"), index=False)

    sku_meta = df_sku.groupby("product_code").agg({
        "product_name":"first","color":"first","line_id_fk":"first",
        "line_name":"first","group_code":"first"}).reset_index()
    sku_t1t2 = (df_sku[df_sku["year_month"].isin(["2026-01","2026-02"])]
                .groupby("product_code")
                .agg(t1t2_rev=("revenue","sum"), t1t2_qty=("qty","sum"))
                .reset_index())
    sku_t1t2 = sku_meta.merge(sku_t1t2, on="product_code", how="left").fillna({"t1t2_rev":0,"t1t2_qty":0})
    g_t1t2 = sku_t1t2.groupby("group_code").agg(g_t1t2_rev=("t1t2_rev","sum"),
                                                  g_t1t2_qty=("t1t2_qty","sum")).reset_index()
    sku_share = sku_t1t2.merge(g_t1t2, on="group_code")
    sku_share["share_rev"] = np.where(sku_share["g_t1t2_rev"]>0, sku_share["t1t2_rev"]/sku_share["g_t1t2_rev"], 0)
    sku_share["share_qty"] = np.where(sku_share["g_t1t2_qty"]>0, sku_share["t1t2_qty"]/sku_share["g_t1t2_qty"], 0)
    fg_base = (fg[fg["scenario"]=="base"][["year_month","group_code","revenue","qty"]]
               .rename(columns={"revenue":"g_pred_rev","qty":"g_pred_qty"}))
    skf = sku_share[["product_code","product_name","color","line_id_fk","line_name",
                     "group_code","share_rev","share_qty"]].merge(fg_base, on="group_code")
    skf["revenue"] = skf["g_pred_rev"] * skf["share_rev"]
    skf["qty"]     = skf["g_pred_qty"] * skf["share_qty"]
    skf = skf.drop(columns=["g_pred_rev","g_pred_qty","share_rev","share_qty"])
    skf.to_parquet(_p("forecast_sku_q2.parquet"), index=False)

    sku_q2 = skf.groupby(["product_code","product_name","color","line_name","group_code"]).agg(
        q2_revenue=("revenue","sum"), q2_qty=("qty","sum")).reset_index()
    top20 = sku_q2.nlargest(20, "q2_revenue").reset_index(drop=True)
    top20["rank"] = top20.index + 1
    top20.to_parquet(_p("forecast_top20_sku.parquet"), index=False)
    print(f"  SKU forecast: {len(skf):,} rows, top20 saved")

# ───────────────── 6. FORECAST Q2 COLOR + SLOW SKU ─────────────────
def forecast_q2_color():
    print("\n[6/8] COLOR TREND + Q2 COLOR SHARE + SLOW SKU")
    df_sku   = pd.read_parquet(_p("df_sku.parquet"))
    df_color = pd.read_parquet(_p("df_color.parquet"))
    fcst_sku = pd.read_parquet(_p("forecast_sku_q2.parquet"))

    col_25 = df_color[df_color["year_month"].isin(Q1_2025)].groupby("color").agg(
        rev_25=("revenue","sum"), qty_25=("qty","sum")).reset_index()
    col_26 = df_color[df_color["year_month"].isin(Q1_2026)].groupby("color").agg(
        rev_26=("revenue","sum"), qty_26=("qty","sum")).reset_index()
    trend = col_25.merge(col_26, on="color", how="outer").fillna(0)
    t25, t26 = trend["rev_25"].sum(), trend["rev_26"].sum()
    trend["share_25"] = trend["rev_25"]/t25*100
    trend["share_26"] = trend["rev_26"]/t26*100
    trend["share_delta"] = trend["share_26"] - trend["share_25"]
    trend = trend[trend["color"].notna()].sort_values("share_26", ascending=False)
    trend.to_parquet(_p("color_trend.parquet"), index=False)

    q2_color = fcst_sku.groupby(["group_code","color"]).agg(
        q2_revenue=("revenue","sum"), q2_qty=("qty","sum")).reset_index()
    q2_color["color"] = q2_color["color"].fillna("NA")
    gtot = q2_color.groupby("group_code")["q2_revenue"].sum().reset_index().rename(columns={"q2_revenue":"g_total"})
    q2_color = q2_color.merge(gtot, on="group_code")
    q2_color["share_pct"] = q2_color["q2_revenue"]/q2_color["g_total"]*100
    q2_color = q2_color.sort_values(["group_code","share_pct"], ascending=[True,False])
    q2_color.to_parquet(_p("forecast_color_q2.parquet"), index=False)

    sku_meta = df_sku.groupby(["product_code","product_name","color","line_name","group_code"]).first().reset_index()[
        ["product_code","product_name","color","line_name","group_code"]]
    q1_26 = df_sku[df_sku["year_month"].isin(Q1_2026)].groupby("product_code").agg(
        q1_26_rev=("revenue","sum"), q1_26_qty=("qty","sum")).reset_index()
    t12 = df_sku[df_sku["year_month"].isin(["2026-01","2026-02"])].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"t12_qty"})
    t3  = df_sku[df_sku["year_month"]=="2026-03"].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"t3_qty"})
    y25 = df_sku[df_sku["year_month"].isin(Q1_2025)].groupby("product_code")["qty"].sum().reset_index().rename(columns={"qty":"q1_25_qty"})
    q2p = fcst_sku.groupby("product_code").agg(q2_pred_rev=("revenue","sum"), q2_pred_qty=("qty","sum")).reset_index()
    slow = (sku_meta.merge(q1_26, on="product_code", how="left")
                    .merge(t12, on="product_code", how="left")
                    .merge(t3, on="product_code", how="left")
                    .merge(y25, on="product_code", how="left")
                    .merge(q2p, on="product_code", how="left")).fillna(0)
    slow["t3_drop"]      = (slow["t12_qty"]>=4) & (slow["t3_qty"] < 0.3*(slow["t12_qty"]/2))
    slow["dead_in_2026"] = (slow["q1_25_qty"]>=5) & (slow["q1_26_qty"]==0)
    slow["pred_drop"]    = (slow["q1_26_rev"]>0) & (slow["q2_pred_rev"] < 0.3*(slow["q1_26_rev"]/3))
    slow["slow_mover"] = slow["t3_drop"] | slow["dead_in_2026"] | slow["pred_drop"]
    slow["reasons"] = slow.apply(
        lambda r: "|".join([t for t,v in [("T3_drop",r["t3_drop"]),
                                          ("dead_2026",r["dead_in_2026"]),
                                          ("pred_drop",r["pred_drop"])] if v]) or "ok", axis=1)
    slow.to_parquet(_p("forecast_slow_sku.parquet"), index=False)
    print(f"  Slow-mover SKUs: {slow['slow_mover'].sum():,}/{len(slow):,}")

# ──────────────────── 7. DEALER BG/NBD ────────────────────
def dealer_forecast():
    print("\n[7/8] DEALER BG/NBD + Gamma-Gamma")
    df_trans = pd.read_parquet(_p("df_dealer_trans.parquet"))
    df_trans["order_date"] = pd.to_datetime(df_trans["order_date"])

    summary = summary_data_from_transaction_data(
        df_trans, customer_id_col="customer_code", datetime_col="order_date",
        monetary_value_col="amount", observation_period_end=OBS_END, freq="D")
    print(f"  Dealers: {len(summary):,}")

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(summary["frequency"], summary["recency"], summary["T"])
    summary["pred_purchases_30d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        30, summary["frequency"], summary["recency"], summary["T"])
    summary["p_order_30d"] = 1 - np.exp(-summary["pred_purchases_30d"])
    summary["p_alive"] = bgf.conditional_probability_alive(
        summary["frequency"], summary["recency"], summary["T"])

    returning = summary[(summary["frequency"]>0) & (summary["monetary_value"]>0)].copy()
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(returning["frequency"], returning["monetary_value"])
    summary["expected_avg_monetary"] = np.nan
    mask = (summary["frequency"]>0) & (summary["monetary_value"]>0)
    summary.loc[mask, "expected_avg_monetary"] = ggf.conditional_expected_average_profit(
        summary.loc[mask, "frequency"], summary.loc[mask, "monetary_value"])
    summary["expected_avg_monetary"] = summary["expected_avg_monetary"].fillna(returning["monetary_value"].median())

    summary["expected_purchases_90d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        90, summary["frequency"], summary["recency"], summary["T"])
    summary["expected_revenue_q2"] = summary["expected_purchases_90d"] * summary["expected_avg_monetary"]
    rev_norm = summary["expected_revenue_q2"] / summary["expected_revenue_q2"].max()
    summary["priority_score"] = (0.5*summary["p_alive"] + 0.5*rev_norm).round(4)
    summary["priority_score_pct"] = summary["priority_score"].rank(pct=True)

    def tier(r):
        if r["p_alive"]<0.2 and r["frequency"]==0: return "4_Lost"
        if r["p_alive"]<0.4: return "3_At_Risk"
        if r["priority_score_pct"]>=0.9: return "1_Champion"
        if r["priority_score_pct"]>=0.6: return "2_Loyal"
        return "3_At_Risk"
    summary["tier"] = summary.apply(tier, axis=1)

    result = summary.reset_index().rename(columns={
        "frequency":"freq_repeat","monetary_value":"avg_monetary_hist","T":"tenure_days"})
    result["expected_revenue_q2"] = result["expected_revenue_q2"].round(0)
    result["expected_avg_monetary"] = result["expected_avg_monetary"].round(0)
    out_cols = ["customer_code","freq_repeat","recency","tenure_days","avg_monetary_hist",
                "p_order_30d","p_alive","expected_avg_monetary","expected_purchases_90d",
                "expected_revenue_q2","priority_score","tier"]
    result[out_cols].to_parquet(_p("dealer_score.parquet"), index=False)
    print(f"  Tier dist: {result['tier'].value_counts().to_dict()}")

# ────────────────────── 8. WRITE TO DB ──────────────────────
TABLES = [
    {"name":"forecast_total","parquet":"forecast_total_q2.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_total(
        year_month VARCHAR(7), scenario VARCHAR(20),
        revenue NUMERIC(18,2), qty NUMERIC(18,2), orders NUMERIC(18,2),
        month_factor NUMERIC(6,3), scenario_factor NUMERIC(6,3))""",
     "cols":["year_month","scenario","revenue","qty","orders","month_factor","scenario_factor"]},
    {"name":"forecast_group","parquet":"forecast_group_q2.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_group(
        year_month VARCHAR(7), group_code VARCHAR(20), group_name VARCHAR(100),
        scenario VARCHAR(20), revenue NUMERIC(18,2), qty NUMERIC(18,2))""",
     "cols":["year_month","group_code","group_name","scenario","revenue","qty"]},
    {"name":"forecast_sku","parquet":"forecast_sku_q2.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_sku(
        product_code VARCHAR(20), product_name VARCHAR(200), color VARCHAR(50),
        line_id INTEGER, line_name VARCHAR(100), group_code VARCHAR(20),
        year_month VARCHAR(7), revenue NUMERIC(18,2), qty NUMERIC(18,2))""",
     "cols":["product_code","product_name","color","line_id_fk","line_name","group_code","year_month","revenue","qty"],
     "col_rename":{"line_id_fk":"line_id"}},
    {"name":"forecast_top20_sku","parquet":"forecast_top20_sku.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_top20_sku(
        rank INTEGER, product_code VARCHAR(20), product_name VARCHAR(200),
        color VARCHAR(50), line_name VARCHAR(100), group_code VARCHAR(20),
        q2_revenue NUMERIC(18,2), q2_qty NUMERIC(18,2))""",
     "cols":["rank","product_code","product_name","color","line_name","group_code","q2_revenue","q2_qty"]},
    {"name":"forecast_color","parquet":"forecast_color_q2.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_color(
        group_code VARCHAR(20), color VARCHAR(50),
        q2_revenue NUMERIC(18,2), q2_qty NUMERIC(18,2),
        g_total NUMERIC(18,2), share_pct NUMERIC(8,4))""",
     "cols":["group_code","color","q2_revenue","q2_qty","g_total","share_pct"]},
    {"name":"color_trend","parquet":"color_trend.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.color_trend(
        color VARCHAR(50),
        rev_25 NUMERIC(18,2), qty_25 NUMERIC(18,2),
        rev_26 NUMERIC(18,2), qty_26 NUMERIC(18,2),
        share_25 NUMERIC(8,4), share_26 NUMERIC(8,4), share_delta NUMERIC(8,4))""",
     "cols":["color","rev_25","qty_25","rev_26","qty_26","share_25","share_26","share_delta"]},
    {"name":"forecast_slow_sku","parquet":"forecast_slow_sku.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.forecast_slow_sku(
        product_code VARCHAR(20), product_name VARCHAR(200), color VARCHAR(50),
        line_name VARCHAR(100), group_code VARCHAR(20),
        q1_26_rev NUMERIC(18,2), q1_26_qty NUMERIC(18,2),
        t12_qty NUMERIC(18,2), t3_qty NUMERIC(18,2), q1_25_qty NUMERIC(18,2),
        q2_pred_rev NUMERIC(18,2), q2_pred_qty NUMERIC(18,2),
        t3_drop BOOLEAN, dead_in_2026 BOOLEAN, pred_drop BOOLEAN,
        slow_mover BOOLEAN, reasons VARCHAR(50))""",
     "cols":["product_code","product_name","color","line_name","group_code",
             "q1_26_rev","q1_26_qty","t12_qty","t3_qty","q1_25_qty",
             "q2_pred_rev","q2_pred_qty","t3_drop","dead_in_2026","pred_drop","slow_mover","reasons"]},
    {"name":"dealer_score","parquet":"dealer_score.parquet",
     "ddl":"""CREATE TABLE tnbike_forecast.dealer_score(
        customer_code VARCHAR(20),
        freq_repeat NUMERIC(10,4), recency NUMERIC(10,4), tenure_days NUMERIC(10,4),
        avg_monetary_hist NUMERIC(18,2),
        p_order_30d NUMERIC(8,6), p_alive NUMERIC(8,6),
        expected_avg_monetary NUMERIC(18,2), expected_purchases_90d NUMERIC(10,4),
        expected_revenue_q2 NUMERIC(18,2), priority_score NUMERIC(8,6), tier VARCHAR(20))""",
     "cols":["customer_code","freq_repeat","recency","tenure_days","avg_monetary_hist",
             "p_order_30d","p_alive","expected_avg_monetary","expected_purchases_90d",
             "expected_revenue_q2","priority_score","tier"]},
]

def write_forecasts_to_db():
    print("\n[8/8] WRITE TO POSTGRES (schema tnbike_forecast)")
    conn = psycopg2.connect(**CONN); conn.autocommit = False; cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS tnbike_forecast")
    for tbl in ["forecast_total","forecast_group","forecast_sku","forecast_top20_sku",
                "forecast_color","color_trend","forecast_slow_sku","dealer_score"]:
        cur.execute(f"DROP TABLE IF EXISTS tnbike.{tbl} CASCADE")

    for t in TABLES:
        df = pd.read_parquet(_p(t["parquet"]))
        rename = t.get("col_rename", {})
        if rename: df = df.rename(columns=rename)
        cols = [rename.get(c, c) for c in t["cols"]]
        df = df[cols].where(pd.notnull(df[cols]), None)
        for c in df.columns:
            if df[c].dtype == bool or df[c].dtype == "boolean":
                df[c] = df[c].astype(bool)
        cur.execute(f"DROP TABLE IF EXISTS tnbike_forecast.{t['name']} CASCADE")
        cur.execute(t["ddl"])
        ph = ", ".join([f'"{c}"' for c in cols])
        sql = f"INSERT INTO tnbike_forecast.{t['name']} ({ph}) VALUES %s"
        rows = [tuple(None if pd.isna(v) else (bool(v) if isinstance(v, np.bool_) else v) for v in r)
                for r in df.itertuples(index=False, name=None)]
        execute_values(cur, sql, rows, page_size=500)
        print(f"  {t['name']:25s} {len(rows):>6,} rows")
    conn.commit(); cur.close(); conn.close()

# ──────────────────────── MAIN ────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print(" PHASE C PIPELINE — Forecast Q2/2026 (TNBike)")
    print("=" * 70)
    build_dataset()
    backtest_total_group()
    backtest_sku()
    backtest_reconciled()
    forecast_q2_sales()
    forecast_q2_color()
    dealer_forecast()
    write_forecasts_to_db()
    print("\n✓ DONE — toàn bộ forecast đã vào schema tnbike_forecast, Power BI có thể refresh.")
