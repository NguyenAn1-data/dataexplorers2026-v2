"""
Phase C - Câu hỏi 3: Dự báo hành vi 798 đại lý

Model: BG/NBD (Beta-Geometric Negative Binomial Distribution) + Gamma-Gamma
       — Khung "buy-till-you-die" cho B2B repeat purchase. Phù hợp với dữ liệu
         sparse (74% đại lý có <4 đơn) vì không cần time-series liên tục.

Outputs:
   C.3.1 — P(order trong 30 ngày tới): conditional_expected_number_of_purchases_up_to_time(30,…)
   C.3.2 — P(alive): conditional_probability_alive(…) — đại lý ngưng hoạt động
   C.3.3 — CLV (Customer Lifetime Value 90 ngày tới) + Priority tier
            • Champion: top 10% CLV
            • Loyal:    next 30% (10-40%)
            • At-Risk:  P_alive < 0.4 hoặc CLV thấp
            • Lost:     P_alive < 0.2 và frequency=0
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
import psycopg2

DATA = os.path.join(os.path.dirname(__file__), "data")
OBS_END = "2026-03-31"

df_trans = pd.read_parquet(os.path.join(DATA, "df_dealer_trans.parquet"))
df_trans["order_date"] = pd.to_datetime(df_trans["order_date"])

# ===== Build RFM-style summary =====
print("=" * 80)
print("BG/NBD - Phân tích 798 đại lý")
print("=" * 80)

summary = summary_data_from_transaction_data(
    df_trans, customer_id_col="customer_code", datetime_col="order_date",
    monetary_value_col="amount", observation_period_end=OBS_END, freq="D"
)
print(f"\nTổng đại lý có giao dịch: {len(summary):,}")
print(f"Phân bố frequency (số lần mua LẶP, không tính lần đầu):")
print(summary["frequency"].describe().to_string())

# ===== Fit BG/NBD =====
bgf = BetaGeoFitter(penalizer_coef=0.01)
bgf.fit(summary["frequency"], summary["recency"], summary["T"])
print(f"\nBG/NBD fitted:")
print(bgf.summary)

# ===== Predict =====
# 1. P(order in next 30 days)
summary["pred_purchases_30d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
    30, summary["frequency"], summary["recency"], summary["T"])
# Convert to probability of at least 1 order (P(X>=1) approx via Poisson)
summary["p_order_30d"] = 1 - np.exp(-summary["pred_purchases_30d"])

# 2. P(alive)
summary["p_alive"] = bgf.conditional_probability_alive(
    summary["frequency"], summary["recency"], summary["T"])

# ===== Fit Gamma-Gamma cho monetary =====
# Yêu cầu: frequency > 0 và monetary_value > 0
returning = summary[(summary["frequency"] > 0) & (summary["monetary_value"] > 0)].copy()
ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(returning["frequency"], returning["monetary_value"])

# Expected average monetary (per transaction) cho từng đại lý
summary["expected_avg_monetary"] = np.nan
mask = (summary["frequency"] > 0) & (summary["monetary_value"] > 0)
summary.loc[mask, "expected_avg_monetary"] = ggf.conditional_expected_average_profit(
    summary.loc[mask, "frequency"], summary.loc[mask, "monetary_value"])
# Đại lý 1 đơn duy nhất → dùng monetary trung bình ngành
fallback_monetary = returning["monetary_value"].median()
summary["expected_avg_monetary"] = summary["expected_avg_monetary"].fillna(fallback_monetary)

# 3. Expected revenue Q2 (90 days)
summary["expected_purchases_90d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
    90, summary["frequency"], summary["recency"], summary["T"])
summary["expected_revenue_q2"] = summary["expected_purchases_90d"] * summary["expected_avg_monetary"]

# Priority score: 0.5*p_alive + 0.5*norm(expected_revenue_q2)
rev_norm = summary["expected_revenue_q2"] / summary["expected_revenue_q2"].max()
summary["priority_score"] = 0.5 * summary["p_alive"] + 0.5 * rev_norm
summary["priority_score"] = summary["priority_score"].round(4)

# Tier classification
def classify_tier(r):
    if r["p_alive"] < 0.2 and r["frequency"] == 0:
        return "4_Lost"
    if r["p_alive"] < 0.4:
        return "3_At_Risk"
    if r["priority_score_pct"] >= 0.9:
        return "1_Champion"
    if r["priority_score_pct"] >= 0.6:
        return "2_Loyal"
    return "3_At_Risk"

summary["priority_score_pct"] = summary["priority_score"].rank(pct=True)
summary["tier"] = summary.apply(classify_tier, axis=1)

# Reset index for output
result = summary.reset_index()
result = result.rename(columns={"frequency":"freq_repeat", "monetary_value":"avg_monetary_hist", "T":"tenure_days"})
result["expected_revenue_q2"] = result["expected_revenue_q2"].round(0)
result["expected_avg_monetary"] = result["expected_avg_monetary"].round(0)

# ===== Reports =====
print("\n" + "=" * 80)
print("C.3.1 — Phân bố P(order 30d)")
print("=" * 80)
print(result["p_order_30d"].describe().to_string())
print(f"\nĐại lý có P(order 30d) ≥ 0.5: {(result['p_order_30d'] >= 0.5).sum():,}")
print(f"Đại lý có P(order 30d) ≥ 0.7: {(result['p_order_30d'] >= 0.7).sum():,}")

print("\n" + "=" * 80)
print("C.3.2 — Đại lý có nguy cơ rời bỏ (P_alive < 0.4)")
print("=" * 80)
churn_risk = result[result["p_alive"] < 0.4].sort_values("expected_revenue_q2", ascending=False)
print(f"\nTổng đại lý rủi ro churn: {len(churn_risk):,} / {len(result):,} ({len(churn_risk)/len(result)*100:.1f}%)")
print(f"\nTop-20 đại lý churn rủi ro cao có doanh thu lớn (giảm sẽ ảnh hưởng nhiều):")
print(f"{'Customer':12s} {'P_alive':>8s} {'P_30d':>7s} {'AvgMon (tr)':>11s} {'ExpRev Q2 (tr)':>14s}")
for _, r in churn_risk.head(20).iterrows():
    print(f"{r['customer_code']:12s} {r['p_alive']:8.3f} {r['p_order_30d']:7.3f} {r['avg_monetary_hist']/1e6:11.1f} {r['expected_revenue_q2']/1e6:14.1f}")

print("\n" + "=" * 80)
print("C.3.3 — Priority tier")
print("=" * 80)
tier_summary = result.groupby("tier").agg(
    n=("customer_code","count"),
    avg_p_alive=("p_alive","mean"),
    avg_p_order=("p_order_30d","mean"),
    total_exp_rev_q2=("expected_revenue_q2","sum"),
).reset_index().sort_values("tier")
tier_summary["total_exp_rev_q2_bil"] = (tier_summary["total_exp_rev_q2"]/1e9).round(2)
print(tier_summary.to_string(index=False))

print(f"\nTop-10 Champion đại lý:")
champion = result[result["tier"]=="1_Champion"].nlargest(10, "expected_revenue_q2")
print(f"{'Customer':12s} {'Freq':>5s} {'P_alive':>8s} {'P_30d':>7s} {'AvgMon (tr)':>11s} {'ExpRev Q2 (tr)':>14s}")
for _, r in champion.iterrows():
    print(f"{r['customer_code']:12s} {r['freq_repeat']:>5.0f} {r['p_alive']:8.3f} {r['p_order_30d']:7.3f} {r['avg_monetary_hist']/1e6:11.1f} {r['expected_revenue_q2']/1e6:14.1f}")

# Lưu
out_cols = ["customer_code","freq_repeat","recency","tenure_days","avg_monetary_hist",
            "p_order_30d","p_alive","expected_avg_monetary","expected_purchases_90d",
            "expected_revenue_q2","priority_score","tier"]
result[out_cols].to_parquet(os.path.join(DATA, "dealer_score.parquet"), index=False)
print(f"\n✓ Đã ghi dealer_score.parquet → {os.path.join(DATA, 'dealer_score.parquet')}")
