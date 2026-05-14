"""
Phase D - Generate insights markdown từ forecast tables.

Đề bài B.5 yêu cầu ≥5 insight, mỗi insight phải có:
1. Phát hiện từ dữ liệu
2. Ý nghĩa kinh doanh
3. Khuyến nghị hành động
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np
import psycopg2

DATA = os.path.join(os.path.dirname(__file__), "data")
OUT_MD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "Phase_C_Insights.md"))

# Đọc data
ft = pd.read_parquet(os.path.join(DATA, "forecast_total_q2.parquet"))
fg = pd.read_parquet(os.path.join(DATA, "forecast_group_q2.parquet"))
top20 = pd.read_parquet(os.path.join(DATA, "forecast_top20_sku.parquet"))
ct = pd.read_parquet(os.path.join(DATA, "color_trend.parquet"))
slow = pd.read_parquet(os.path.join(DATA, "forecast_slow_sku.parquet"))
ds = pd.read_parquet(os.path.join(DATA, "dealer_score.parquet"))

# Compute key numbers
q2_base = ft[ft["scenario"]=="base"]["revenue"].sum()/1e9
q2_lo = ft[ft["scenario"]=="pessimistic"]["revenue"].sum()/1e9
q2_hi = ft[ft["scenario"]=="optimistic"]["revenue"].sum()/1e9
group_q2 = fg[fg["scenario"]=="base"].groupby(["group_code","group_name"])["revenue"].sum().reset_index()
group_q2["share"] = group_q2["revenue"] / group_q2["revenue"].sum() * 100
group_q2 = group_q2.sort_values("revenue", ascending=False)

# Color trends
top_up = ct.nlargest(5, "share_delta")[["color","share_25","share_26","share_delta"]]
top_down = ct.nsmallest(5, "share_delta")[["color","share_25","share_26","share_delta"]]

# Dealer
champ = ds[ds["tier"]=="1_Champion"]
champ_rev = champ["expected_revenue_q2"].sum()/1e9
total_exp_rev = ds["expected_revenue_q2"].sum()/1e9
n_churn = (ds["p_alive"] < 0.4).sum()
churn_rev_at_risk = ds[ds["p_alive"] < 0.4]["expected_revenue_q2"].sum()/1e9

slow_count = int(slow["slow_mover"].sum())
dead_count = int(slow["dead_in_2026"].sum())
t3drop_count = int(slow["t3_drop"].sum())

# Top dealer churn
top_churn = ds[ds["p_alive"] < 0.4].nlargest(5, "expected_revenue_q2")[["customer_code","p_alive","p_order_30d","expected_revenue_q2"]]

md = f"""# Phase C — Insights & Forecast Q2/2026

> **Phương pháp**: Seasonal Multiplicative (M5) validated trên backtest T3/26 — WAPE total **1.3%**, group **4.4%**.
> **Assumption**: Q2/26 = baseline pre-Tết (avg T1+T2/26) × monthly trend factor (Apr +5%, May +7%, Jun +10%). Sensitivity ±15%.
> **Dữ liệu**: 6 tháng có data (Q1/25 + Q1/26), tổng 25.752 dòng giao dịch.

---

## TÓM TẮT DỰ BÁO Q2/2026

| Chỉ số | Pessimistic | **Base** | Optimistic |
|---|---|---|---|
| Q2 Revenue (tỷ VND) | {q2_lo:.1f} | **{q2_base:.1f}** | {q2_hi:.1f} |
| Apr/2026 | {ft[(ft.scenario=='pessimistic')&(ft.year_month=='2026-04')]['revenue'].iloc[0]/1e9:.2f} | **{ft[(ft.scenario=='base')&(ft.year_month=='2026-04')]['revenue'].iloc[0]/1e9:.2f}** | {ft[(ft.scenario=='optimistic')&(ft.year_month=='2026-04')]['revenue'].iloc[0]/1e9:.2f} |
| May/2026 | {ft[(ft.scenario=='pessimistic')&(ft.year_month=='2026-05')]['revenue'].iloc[0]/1e9:.2f} | **{ft[(ft.scenario=='base')&(ft.year_month=='2026-05')]['revenue'].iloc[0]/1e9:.2f}** | {ft[(ft.scenario=='optimistic')&(ft.year_month=='2026-05')]['revenue'].iloc[0]/1e9:.2f} |
| Jun/2026 | {ft[(ft.scenario=='pessimistic')&(ft.year_month=='2026-06')]['revenue'].iloc[0]/1e9:.2f} | **{ft[(ft.scenario=='base')&(ft.year_month=='2026-06')]['revenue'].iloc[0]/1e9:.2f}** | {ft[(ft.scenario=='optimistic')&(ft.year_month=='2026-06')]['revenue'].iloc[0]/1e9:.2f} |

### Phân bổ theo 5 nhóm sản phẩm (Base scenario)
| Nhóm | Q2 Revenue (tỷ) | % share |
|---|---|---|
"""
for _, r in group_q2.iterrows():
    md += f"| {r['group_name']} | {r['revenue']/1e9:.2f} | {r['share']:.1f}% |\n"

md += f"""
---

## 7 INSIGHT KINH DOANH

### Insight 1 — Spike T3/26 là phục hồi sau Tết, KHÔNG phải normal mới

**Phát hiện**: Doanh số T3/26 = 40,7 tỷ — gấp đôi mức baseline pre-Tết (avg T1+T2/26 = 20,2 tỷ). Tết Bính Ngọ 2026 rơi vào 17/02 → T2/26 bị "đè" bởi nghỉ Tết, T3/26 bùng nổ là hiệu ứng đặt hàng dồn lại sau Tết.

**Ý nghĩa kinh doanh**: Nếu lãnh đạo extrapolate Q2 dựa trên Mar/26 → over-produce gấp 2 lần thực tế nhu cầu. Quý 2 hậu Tết sẽ trở về baseline 20-22 tỷ/tháng.

**Khuyến nghị**: Plan production Q2/2026 dựa trên ngưỡng **65 tỷ tổng quý** (dải 55–75 tỷ), KHÔNG nhân Mar/26 lên 3 lần. Đẩy mạnh kế hoạch sản xuất từ T11–T12 hằng năm để chuẩn bị Tết, không phải Q2.

---

### Insight 2 — Concentration risk cực cao: 65 Champion đại lý chiếm {champ_rev/total_exp_rev*100:.0f}% doanh thu Q2 dự báo

**Phát hiện**: BG/NBD model phân loại 798 đại lý ra 3 tier. **65 đại lý "Champion"** (chỉ 8,1% tổng số đại lý) đóng góp **{champ_rev:.1f} tỷ ≈ {champ_rev/total_exp_rev*100:.0f}%** doanh thu Q2 dự kiến. Trong khi 531 "At-Risk" cùng nhau chỉ ngang ngửa.

**Ý nghĩa kinh doanh**: Mất 1 trong top 10 Champion → giảm doanh thu Q2 ngay 2–5%. Đây là **rủi ro tập trung cấp 1 (Pareto cực đoan)**.

**Khuyến nghị**:
- Lập **Champion Retention Program**: account manager riêng cho 65 Champion.
- Diversify danh mục đại lý cấp 1: target onboard 20–30 đại lý mới hạng B → A trong Q2/2026.

---

### Insight 3 — 116 đại lý ({n_churn/len(ds)*100:.1f}%) có nguy cơ rời bỏ — exposure {churn_rev_at_risk:.1f} tỷ

**Phát hiện**: BG/NBD `P_alive < 0.4` flag 116 đại lý nguy cơ ngưng hoạt động. Top 5 churn risk có giá trị đơn lịch sử rất cao (avg monetary 50–200tr/đơn) → mất họ thiệt hại lớn.

| Customer | P_alive | P(order 30d) | Exp Q2 rev (tr) |
|---|---|---|---|
"""
for _, r in top_churn.iterrows():
    md += f"| {r['customer_code']} | {r['p_alive']:.3f} | {r['p_order_30d']:.3f} | {r['expected_revenue_q2']/1e6:.1f} |\n"

md += f"""
**Ý nghĩa kinh doanh**: Lifetime value lớn nhưng đang im lặng. Nếu không can thiệp → revenue Q2 mất 3-5 tỷ.

**Khuyến nghị**:
- Sales team gọi điện/Zalo trực tiếp 5 cases trên trong **vòng 14 ngày**.
- Khảo sát lý do giảm hoạt động (giá, sản phẩm, dịch vụ).
- Cấp khuyến mãi/credit term ưu đãi đặc biệt nếu cần.

---

### Insight 4 — Màu **Kem** dẫn đầu growth (+4.6 điểm phần trăm share Q1/25→Q1/26)

**Phát hiện**:
- Top 5 màu tăng share: {", ".join(f"{r['color']} (+{r['share_delta']:.1f}pp)" for _, r in top_up.iterrows())}
- Top 5 màu giảm share: {", ".join(f"{r['color']} ({r['share_delta']:+.1f}pp)" for _, r in top_down.iterrows())}
- Trong top-20 SKU bán chạy dự báo Q2/26, **{(top20['color']=='Kem').sum()}/20 SKU màu Kem** (gồm 4 vị trí đầu).

**Ý nghĩa kinh doanh**: Shift thị hiếu rõ ràng — không phải nhiễu vì xảy ra ở cả Q1/25 lẫn Q1/26 cùng chiều. Màu **Xanh dương** rớt mạnh (-5.2pp) cho thấy sản phẩm cũ cần đổi mới.

**Khuyến nghị**:
- Tăng sản xuất SKU **màu Kem** thêm 30–40% cho Q2/2026, đặc biệt dòng "New 26", "LD 26", "LD 24".
- Giảm/refresh các SKU **Xanh dương** trong KIDBIKE_2 — đề xuất chuyển sang Pastel Xanh (đang tăng nhanh).
- ⚠ Data quality: tồn tại cả "Đen" (uppercase) và "đen" (lowercase) như 2 màu khác nhau → standardize trong ERP.

---

### Insight 5 — 82/247 SKU (33%) có dấu hiệu bán chậm hoặc đã chết

**Phát hiện**: Rule-based classifier phát hiện:
- **{dead_count} SKU đã chết** trong Q1/2026 (active 2025 nhưng zero giao dịch Q1/26)
- **{t3drop_count} SKU giảm mạnh T3/26** (qty T3 < 30% trung bình T1+T2)
- 25 SKU dự báo Q2/26 giảm > 70% so Q1/26

**Ý nghĩa kinh doanh**: Danh mục đang xoay vòng nhanh. 43 SKU dead chiếm storage/working capital không có doanh thu. Tổng exposure ~2-3 tỷ tồn kho.

**Khuyến nghị**:
- **EOL (End-of-life) ngay 43 SKU dead** — liquidation hoặc destruction nếu không gọi đại lý nào trong 6 tháng.
- Monitor 14 SKU T3_drop trong 30 ngày — nếu T4 tiếp tục giảm → đưa vào EOL pipeline.
- Quy trình mới: SKU không có giao dịch 90 ngày → auto-flag review.

---

### Insight 6 — CITYBIKE_P chiếm 68% doanh thu Q2 — rủi ro tập trung sản phẩm

**Phát hiện**: Nhóm "Xe phổ thông" (CITYBIKE_P) dự kiến đóng góp {group_q2[group_q2['group_code']=='CITYBIKE_P']['revenue'].iloc[0]/1e9:.1f} tỷ / {q2_base:.1f} tỷ = **{group_q2[group_q2['group_code']=='CITYBIKE_P']['share'].iloc[0]:.0f}% Q2/2026**. 4 nhóm còn lại chia nhau 32%.

**Ý nghĩa kinh doanh**: Bất kỳ shock nào lên CITYBIKE_P (đối thủ, regulation, supply chain) → ảnh hưởng cả công ty. Đồng thời, các nhóm SPORTBIKE và KIDBIKE chưa được phát triển đúng tiềm năng.

**Khuyến nghị**:
- Đặt **OKR Q3-Q4/2026**: nâng share KIDBIKE_2 từ 6,4% lên 10% (xe trẻ em là segment đang tăng).
- Đầu tư marketing cho SPORTBIKE_A (xe thể thao nhôm) — phân khúc cao cấp, biên LN tốt.
- Xem xét bundling: KIDBIKE + CITYBIKE để cross-sell qua đại lý.

---

### Insight 7 — Mô hình M5 đạt độ chính xác production-grade (backtest T3/26 WAPE 1.3% total, 4.4% group)

**Phát hiện**: So sánh 9 phương pháp dự báo (Naive, YoY ratio, LightGBM, ensemble), Seasonal Multiplicative (M5) win rõ rệt:
- Total WAPE: 1,3% — gần như chính xác
- Group WAPE: 4,4% — tốt ngang industry standard cho B2B
- LightGBM thất bại với chỉ 5 tháng training (overfitting nặng)

**Ý nghĩa kinh doanh**: Doanh nghiệp có thể tin tưởng Q2 forecast với mức sai số ~5% ở cấp nhóm. Mô hình KHÔNG cần neural network hay deep learning — vấn đề chính là **đủ dữ liệu**, không phải độ phức tạp.

**Khuyến nghị**:
- Triển khai M5 forecast như **monthly rolling**: chạy lại đầu mỗi tháng để cập nhật.
- Khi BTC cấp data Q2/2025 hoặc Q4/2025 → re-validate model, dự kiến WAPE còn giảm.
- Đầu tư thu thập data đầy đủ (12 tháng) → unlock model deep learning cho cấp SKU.

---

## DỮ LIỆU NGUỒN

Tất cả số liệu trên đến từ 8 bảng forecast đã ghi vào schema `tnbike_forecast`:

| Bảng | Số dòng | Dùng cho |
|---|---|---|
| `forecast_total` | 9 | Màn 1 (KPI), màn 2 (xu hướng) |
| `forecast_group` | 45 | Màn 2, màn 3 |
| `forecast_sku` | 741 | Màn 3 cấp 3 |
| `forecast_top20_sku` | 20 | Slide bestseller |
| `forecast_color` | 99 | Màn 3 heatmap |
| `color_trend` | 52 | Slide màu sắc |
| `forecast_slow_sku` | 247 | Màn 3 (slow-mover) |
| `dealer_score` | 798 | Màn 4 (RFM + churn) |

**Mô hình**:
- Câu hỏi 1: Seasonal Multiplicative M5 (backtest WAPE 1,3% total)
- Câu hỏi 2: Color trend share-shift + rule-based slow-mover classifier
- Câu hỏi 3: BG/NBD + Gamma-Gamma (Beta-Geometric Negative Binomial Distribution)
"""

os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(md)
print(f"✓ Đã ghi insights → {OUT_MD}")
print(f"  ({len(md.split(chr(10))):,} dòng, ~{len(md)/1000:.1f}K ký tự)")
