# Phase C — Dự báo nhu cầu Q2/2026

Module forecasting cho cuộc thi DataExplorers2026 Vòng 2.

## Cấu trúc

```
forecast/
├─ README.md                ← file này
├─ pipeline_forecast.py     ← ⭐ TOÀN BỘ Phase C trong 1 file — chạy 1 lệnh là xong
├─ 09_generate_insights.py  ← (Phase D) sinh markdown insights từ kết quả forecast
└─ data/                    ← parquet artifacts (sinh khi chạy, không push lên Git)
```

## Cách chạy

```powershell
# 1. Cài thư viện
pip install pandas numpy scikit-learn scipy statsmodels lightgbm lifetimes psycopg2 pyarrow

# 2. Đảm bảo PostgreSQL `tnbike_db` đã có schema `tnbike` + bảng `fact_sales`
#    (chạy folder pipeline/ trước nếu chưa có)

# 3. Chạy toàn bộ Phase C bằng 1 lệnh
python forecast/pipeline_forecast.py

# 4. (tùy chọn) Sinh markdown insights cho Phase D
python forecast/09_generate_insights.py
```

File `pipeline_forecast.py` gồm 8 function gọi tuần tự trong `__main__`:

`build_dataset` → `backtest_total_group` → `backtest_sku` → `backtest_reconciled` → `forecast_q2_sales` → `forecast_q2_color` → `dealer_forecast` → `write_forecasts_to_db`

Kết quả: 8 bảng forecast trong schema `tnbike_forecast` của PostgreSQL + parquet ở `forecast/data/`, sẵn cho Power BI refresh.

## Phương pháp

### Câu hỏi 1 — Dự báo doanh số Q2/2026

**Model**: Seasonal Multiplicative (M5)
```
T3/26_pred = avg(T1/26, T2/26) × (T3/25 / mean(Q1/25))
```

**Backtest validation** trên T3/2026 (đã có actual):

| Cấp | M5 WAPE | Đối chiếu LightGBM |
|---|---|---|
| Total | **1,3%** | n/a |
| 5 nhóm | **4,4%** | 45,3% |
| Top-20 SKU | **19,5%** | 59,0% |
| Group rollup từ SKU | **7,0%** | 29,0% |

→ M5 được chọn cho production forecast. LightGBM bị overfitting do chỉ có 5 tháng training × 5 series = 25 rows training data.

**Forecast Q2/2026** (Apr/May/Jun):
- Vì KHÔNG có dữ liệu Q2/2025 lịch sử, không thể tính seasonal index năm cho Q2 → assumption-based.
- **Base scenario**: Q2 = baseline pre-Tết (avg T1+T2/26 ≈ 20,2 tỷ/tháng) × trend factor (Apr ×1,05, May ×1,07, Jun ×1,10).
- **Sensitivity**: ±15% (lạc quan / thận trọng).
- Top-down: 5 nhóm → 247 SKU theo share (T1+T2)/2026.

### Câu hỏi 2 — Màu sắc + SKU bán chậm

- **Color trend**: so sánh share màu Q1/2025 vs Q1/2026 → trend dương/âm.
- **Color Q2/2026 share**: aggregate SKU forecast Q2 theo (group, color) → tỷ trọng dự kiến.
- **Slow-mover**: rule-based classifier với 3 tiêu chí:
  - `t3_drop`: T3/26 qty < 30% trung bình T1+T2/26
  - `dead_in_2026`: active 2025 nhưng zero Q1/26
  - `pred_drop`: Q2 forecast revenue < 30% Q1/26 actual

### Câu hỏi 3 — Hành vi đại lý

**Model**: BG/NBD (Beta-Geometric Negative Binomial Distribution) + Gamma-Gamma
- Thư viện: `lifetimes` (https://github.com/CamDavidsonPilon/lifetimes)
- Input: transaction-level data của 798 đại lý
- Outputs:
  - `p_order_30d`: xác suất đặt hàng trong 30 ngày tới
  - `p_alive`: xác suất đại lý còn "sống"
  - `expected_revenue_q2`: kỳ vọng doanh thu Q2/26 từ đại lý đó
  - `priority_score`: 0.5 × p_alive + 0.5 × normalized_expected_revenue
  - `tier`: Champion / Loyal / At-Risk

**Tại sao BG/NBD không phải time-series**: 74% đại lý có <4 đơn → quá sparse cho time-series per-customer. BG/NBD chỉ cần RFM (recency, frequency, monetary), không cần lịch sử tháng liên tục.

## Output

### Schema PostgreSQL `tnbike_forecast` (tách biệt khỏi schema gốc `tnbike` của BTC)

| Bảng | Rows | Mô tả |
|---|---|---|
| `forecast_total` | 9 | 3 tháng × 3 kịch bản, doanh thu/qty/đơn |
| `forecast_group` | 45 | 5 nhóm × 3 tháng × 3 kịch bản |
| `forecast_sku` | 741 | 247 SKU × 3 tháng (base) |
| `forecast_top20_sku` | 20 | Top-20 SKU dự kiến bán chạy Q2 |
| `forecast_color` | 99 | (group × color) share Q2 |
| `color_trend` | 52 | Share màu Q1/25 vs Q1/26 |
| `forecast_slow_sku` | 247 | SKU + flag slow-mover |
| `dealer_score` | 798 | RFM + BG/NBD scores + tier |

### Parquet local

Tất cả output cũng được lưu ở `forecast/data/*.parquet` để chạy lại không cần DB.

## Ràng buộc dữ liệu quan trọng

- **Chỉ 6 tháng có data**: T1/25, T2/25, T3/25, T1/26, T2/26, T3/26.
- **9 tháng trống**: 04/2025 → 12/2025 (Q2+Q3+Q4 năm 2025 không tồn tại trong DB).
- **0/265 SKU có ≥12 tháng lịch sử** → không thể fit ARIMA/SARIMA per-SKU.
- **Q2/2026 không có precedent năm trước** → forecast Q2 dựa trên assumption, không phải seasonal index.

Đây là lý do chọn M5 (đơn giản, robust) thay vì model phức tạp.

## Tóm tắt số liệu Q2/2026 (Base scenario)

| Tháng | Revenue (tỷ VND) | Qty | Orders |
|---|---|---|---|
| Apr | 21,28 | 13.159 | 491 |
| May | 21,68 | 13.410 | 500 |
| Jun | 22,29 | 13.785 | 514 |
| **Q2 TOTAL** | **65,2** | **40.354** | **1.505** |

Dải sensitivity: 55,5 – 75,0 tỷ.
