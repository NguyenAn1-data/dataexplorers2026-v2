# DataExplorers 2026 – Vòng 2
### From Data to Decision 
**Nhóm DataSync**

---

## Thành viên nhóm

| Họ và tên | Vai trò |
|---|---|
| Nguyễn Đăng Hoàng Ân | Nhóm trưởng |
| Lê Thiên Đức | Thành viên |
| Tạ Ngọc Bảo Ngân | Thành viên |
| Nguyễn Trang Nhật Mai | Thành viên |
| Nguyễn Quỳnh Trâm | Thành viên |

---

### Kiến trúc pipeline

```
1.132 file .eml
      │
      ▼
 parse_eml.py        ← Phân tích email: From, Subject, Date, Message-ID, PDF attachment
      │
      ▼
 parse_pdf.py        ← Trích xuất PDF: số đơn, ngày, MST, tên KH, bảng sản phẩm
      │
      ▼
 clean_all.py        ← Làm sạch & kiểm tra hợp lệ: trùng lặp, ngày tháng, mã hàng
      │
      ▼
 db_writer.py        ← Ghi vào PostgreSQL: email_log → sales_order → order_line → fact_sales
```

### Các bảng database được cập nhật

| Bảng | Số dòng T3/2026 | Mô tả |
|---|---|---|
| `email_log` | 1.132 rows | Trạng thái xử lý từng email |
| `sales_order` | 1.132 rows | Đơn hàng BH26.0935 → BH26.2066 |
| `order_line` | 8.721 rows | Chi tiết sản phẩm từng đơn |
| `fact_sales` | 8.721 rows | Bảng phân tích doanh thu |

---

## Cài đặt & Chạy Pipeline 

> Đọc toàn bộ hướng dẫn này trước khi bắt đầu. Mỗi bước phải hoàn thành mới chạy bước tiếp theo.

---

### Bước 0: Cài đặt phần mềm cần thiết

Nếu máy bạn đã có sẵn Python và PostgreSQL, bỏ qua bước này.

#### 0a. Cài Python 3.11+
1. Truy cập: https://www.python.org/downloads/
2. Tải bản **Python 3.11** hoặc mới hơn (không dùng bản 3.12+ nếu gặp lỗi psycopg2)
3. Chạy file cài đặt — **tick vào ô "Add Python to PATH"** trước khi bấm Install
4. Mở Command Prompt, kiểm tra:
```
python --version
```
Phải ra `Python 3.11.x` hoặc cao hơn.

#### 0b. Cài PostgreSQL 14+
1. Truy cập: https://www.postgresql.org/download/
2. Tải bản **PostgreSQL 14** hoặc mới hơn
3. Cài đặt mặc định, **nhớ password bạn đặt cho user `postgres`** — sẽ dùng ở Bước 3
4. Port mặc định: `5432` (giữ nguyên)
5. Sau cài đặt, mở pgAdmin để kiểm tra kết nối

#### 0c. Cài Git
1. Truy cập: https://git-scm.com/downloads
2. Cài đặt mặc định (Next liên tục)
3. Kiểm tra: `git --version`

---

### Bước 1: Clone repo về máy

Mở Command Prompt hoặc PowerShell, chạy:

```bash
git clone https://github.com/NguyenAn1-data/dataexplorers2026-v2.git
cd dataexplorers2026-v2
```

Sau bước này bạn đang ở thư mục `dataexplorers2026-v2\`. **Giữ nguyên thư mục này** cho các bước tiếp theo.

---

### Bước 2: Cài thư viện Python

**Vẫn đứng tại thư mục `dataexplorers2026-v2\`**, chạy:

```bash
pip install -r pipeline/requirements.txt
```

Nếu lệnh trên báo lỗi `No such file or directory`, cài thủ công bằng lệnh sau:

```bash
pip install psycopg2-binary==2.9.9 pdfplumber==0.10.3 tqdm==4.66.1 openpyxl pandas python-dotenv
```

Chờ đến khi cài xong (có thể mất 2–5 phút tùy tốc độ mạng).

---

### Bước 3: Cấu hình kết nối database

#### 3a. Tạo file config

**Windows (Command Prompt):**
```cmd
copy pipeline\config.example.py pipeline\config.py
```

**Windows (PowerShell):**
```powershell
Copy-Item pipeline\config.example.py pipeline\config.py
```

**Mac / Linux:**
```bash
cp pipeline/config.example.py pipeline/config.py
```

#### 3b. Mở và sửa file `pipeline\config.py`

Mở bằng Notepad hoặc bất kỳ trình soạn thảo nào, sửa hai dòng sau:

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "tnbike_db",
    "user":     "postgres",
    "password": "ĐÂY_LÀ_PASSWORD_POSTGRESQL_CỦA_BẠN",   # ← SỬA Ở ĐÂY
    "options":  "-c search_path=tnbike,public",
}

EML_FOLDER = r"C:\Users\TenBan\Downloads\eml_files"      # ← ĐƯỜNG DẪN THƯ MỤC CHỨA FILE .eml
```

> `password`: Chính xác là password bạn đặt lúc cài PostgreSQL  
> `EML_FOLDER`: Đường dẫn đầy đủ đến thư mục chứa 1.132 file `.eml`

---

### Bước 4: Vào thư mục pipeline và khởi tạo database

```bash
cd pipeline
python setup_db.py
```

**Output dự kiến:**
```
✓ Tạo database tnbike_db...
✓ Schema tạo thành công!
✓ Dữ liệu lịch sử import thành công!
======================================================================
✓ SETUP DATABASE THÀNH CÔNG!
```

Nếu thấy lỗi `password authentication failed` → kiểm tra lại password trong `config.py`.  
Nếu thấy lỗi `could not connect to server` → kiểm tra PostgreSQL đang chạy chưa (mở Services hoặc pgAdmin).

---

### Bước 5: Chạy pipeline

**Vẫn đứng tại thư mục `pipeline\`**, chạy:

```bash
python main.py
```

Chờ khoảng **4–10 phút**. Thanh tiến trình sẽ hiện:

```
✓ Kết nối PostgreSQL thành công
✓ Tìm thấy 1132 file .eml

Xử lý email: 100%|████████████████| 1132/1132 [04:23<00:00]
```

**Output cuối khi thành công:**
```
======================================================================
KẾT QUẢ PIPELINE PHASE A
======================================================================
SUCCESS:         1132 đơn hàng
DUPLICATE:          0 đơn
ERROR:              0 đơn
LINES:           8721 dòng sản phẩm
======================================================================
Database stats (T3/2026):
  sales_order: 1132 rows
  order_line:  8721 rows
  Doanh thu:   40,700,000,000 VND
======================================================================
```

---

## Cấu trúc thư mục

```
dataexplorers2026-v2/
├── README.md
├── .gitignore
├── pipeline/
│   ├── main.py                      # ← CHẠY CÁI NÀY! Điều phối toàn bộ pipeline
│   ├── setup_db.py                  # ← Khởi tạo database (chạy 1 lần đầu)
│   ├── parse_eml.py                 # Parser file .eml
│   ├── parse_pdf.py                 # Parser PDF bằng pdfplumber
│   ├── db_writer.py                 # Ghi vào PostgreSQL
│   ├── clean_all.py                 # Cleaning & validation dữ liệu
│   ├── config.example.py            # Template cấu hình (copy → config.py)
│   ├── config.py                    # Cấu hình database (TỰ TẠO từ example, không có sẵn)
│   ├── requirements.txt             # Danh sách thư viện Python
│   └── logs/                        # Thư mục log (tự tạo khi chạy)
├── forecast/                        # Phase C — Dự báo Q2/2026
└── docs/                            # Báo cáo kỹ thuật
```

---

## Hạng mục C — Dự báo nhu cầu Q2/2026

Module forecasting cho cuộc thi DataExplorers2026 Vòng 2.

### Cấu trúc

```
forecast/
├─ pipeline_forecast.py     ← ⭐ TOÀN BỘ Phase C trong 1 file — chạy 1 lệnh là xong
├─ 09_generate_insights.py  ← (Phase D) sinh markdown insights từ kết quả forecast
└─ data/                    ← parquet artifacts (sinh khi chạy, không push lên Git)
```

### Yêu cầu hệ thống (Phase C)

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | ≥ 3.9 (khuyến nghị 3.10/3.11) | `lifetimes` chưa hỗ trợ 3.12 ổn định |
| PostgreSQL | ≥ 13 | Đã chạy local trên `localhost:5432` |
| RAM | ≥ 4 GB | LightGBM + parquet đọc cùng lúc |
| OS | Windows / macOS / Linux | Test trên Windows 11 + PowerShell |

### Bước C1 — Đảm bảo database đã có data

Pipeline đọc từ bảng `tnbike.fact_sales`. Nếu bạn **chưa chạy Phase A** (Bước 0–5 ở trên), hãy chạy trước để dựng schema và import dữ liệu.

Kiểm tra DB đã sẵn sàng:

```powershell
psql -U postgres -d tnbike_db -c "SELECT COUNT(*) FROM tnbike.fact_sales;"
# Kỳ vọng: ~9.000+ rows trải 6 tháng (T1/25..T3/25, T1/26..T3/26)
```

### Bước C2 — Cấu hình DB cho pipeline_forecast.py

Mặc định pipeline đang hard-code credentials trong `forecast/pipeline_forecast.py` dòng ~30:

```python
CONN = dict(host="localhost", dbname="tnbike_db", user="postgres", password="123456")
```

**Nếu user/password Postgres của bạn khác**, hãy sửa dòng trên trước khi chạy.

### Bước C3 — Cài thư viện cho Phase C

```powershell
# (Khuyến nghị) tạo venv riêng
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # macOS / Linux

# Cài thư viện
pip install --upgrade pip
pip install pandas numpy scikit-learn scipy statsmodels lightgbm lifetimes psycopg2-binary pyarrow
```

> **Lưu ý Windows:** dùng `psycopg2-binary` (không cần build từ source). Nếu Python 3.12+ gặp lỗi cài `lifetimes`, hãy hạ xuống Python 3.10 hoặc 3.11.

### Bước C4 — Chạy toàn bộ Phase C

```powershell
python forecast/pipeline_forecast.py
```

Quá trình mất khoảng **30 giây – 2 phút** tùy máy. Bạn sẽ thấy log dạng:

```
======================================================================
 PHASE C PIPELINE — Forecast Q2/2026 (TNBike)
======================================================================

[1/8] BUILD DATASET
  fact rows: 9,XXX  months: ['2025-01', ..., '2026-03']
[2/8] BACKTEST TOTAL + GROUP
  TOTAL Actual T3/26: 21.XX tỷ
[3/8] BACKTEST SKU ...
[4/8] BACKTEST RECONCILED ...
[5/8] FORECAST Q2/2026 SALES
  Q2 BASE total revenue: 65.25 tỷ
[6/8] COLOR TREND + Q2 COLOR SHARE + SLOW SKU
[7/8] DEALER BG/NBD + Gamma-Gamma
  Dealers: 798
[8/8] WRITE TO POSTGRES (schema tnbike_forecast)
✓ DONE — toàn bộ forecast đã vào schema tnbike_forecast, Power BI có thể refresh.
```

8 function gọi tuần tự trong `__main__`:
`build_dataset` → `backtest_total_group` → `backtest_sku` → `backtest_reconciled` → `forecast_q2_sales` → `forecast_q2_color` → `dealer_forecast` → `write_forecasts_to_db`

### Bước C5 — Verify kết quả

```powershell
# Đếm rows trong 8 bảng forecast
psql -U postgres -d tnbike_db -c "
  SELECT table_name,
         (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) AS c FROM tnbike_forecast.'||table_name, true, true, '')))[1]::text::int AS rows
  FROM information_schema.tables
  WHERE table_schema='tnbike_forecast' ORDER BY table_name;
"
```

Hoặc đơn giản hơn — kiểm tra file parquet đã sinh:

```powershell
dir forecast\data\*.parquet
# Kỳ vọng: 16 file parquet
```

### Bước C6 (tùy chọn) — Sinh markdown insights cho Phase D

```powershell
python forecast/09_generate_insights.py
# Output: docs/Phase_C_Insights.md
```

### Troubleshooting

| Lỗi | Cách xử lý |
|---|---|
| `psycopg2.OperationalError: could not connect` | Postgres chưa chạy, sai host/port/user. Kiểm tra service `postgresql` đang chạy + sửa `CONN` trong `pipeline_forecast.py`. |
| `relation "tnbike.fact_sales" does not exist` | Chưa chạy Phase A (Bước 0–5 ở trên). Quay lại pipeline xử lý email. |
| `ModuleNotFoundError: No module named 'lifetimes'` | Activate venv chưa đúng, hoặc dùng Python 3.12+ → hạ xuống 3.10/3.11. |
| `UnicodeEncodeError` trên Windows | Chạy bằng PowerShell (không phải cmd cũ). File đã set `sys.stdout` UTF-8. |
| Kết quả WAPE rất khác README | DB của bạn có data khác — pipeline tự thích nghi, đó là bình thường. |

Kết quả cuối: 8 bảng forecast trong schema `tnbike_forecast` của PostgreSQL + 16 file parquet ở `forecast/data/`, sẵn cho Power BI refresh.

### Phương pháp

#### Câu hỏi 1 — Dự báo doanh số Q2/2026

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

#### Câu hỏi 2 — Màu sắc + SKU bán chậm

- **Color trend**: so sánh share màu Q1/2025 vs Q1/2026 → trend dương/âm.
- **Color Q2/2026 share**: aggregate SKU forecast Q2 theo (group, color) → tỷ trọng dự kiến.
- **Slow-mover**: rule-based classifier với 3 tiêu chí:
  - `t3_drop`: T3/26 qty < 30% trung bình T1+T2/26
  - `dead_in_2026`: active 2025 nhưng zero Q1/26
  - `pred_drop`: Q2 forecast revenue < 30% Q1/26 actual

#### Câu hỏi 3 — Hành vi đại lý

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

### Output Phase C

#### Schema PostgreSQL `tnbike_forecast` (tách biệt khỏi schema gốc `tnbike` của BTC)

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

#### Parquet local

Tất cả output cũng được lưu ở `forecast/data/*.parquet` để chạy lại không cần DB.

### Ràng buộc dữ liệu quan trọng

- **Chỉ 6 tháng có data**: T1/25, T2/25, T3/25, T1/26, T2/26, T3/26.
- **9 tháng trống**: 04/2025 → 12/2025 (Q2+Q3+Q4 năm 2025 không tồn tại trong DB).
- **0/265 SKU có ≥12 tháng lịch sử** → không thể fit ARIMA/SARIMA per-SKU.
- **Q2/2026 không có precedent năm trước** → forecast Q2 dựa trên assumption, không phải seasonal index.

Đây là lý do chọn M5 (đơn giản, robust) thay vì model phức tạp.

### Tóm tắt số liệu Q2/2026 (Base scenario)

| Tháng | Revenue (tỷ VND) | Qty | Orders |
|---|---|---|---|
| Apr | 21,28 | 13.159 | 491 |
| May | 21,68 | 13.410 | 500 |
| Jun | 22,29 | 13.785 | 514 |
| **Q2 TOTAL** | **65,2** | **40.354** | **1.505** |

Dải sensitivity: 55,5 – 75,0 tỷ.

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.11+ |
| PDF parsing | pdfplumber |
| Database | PostgreSQL 14+ (psycopg2-binary) |
| Email parsing | Python `email` module (stdlib) |
| Dashboard | Power BI Desktop (kết nối PostgreSQL) |
| Forecasting | LightGBM, lifetimes (BG/NBD), statsmodels, M5 Seasonal Multiplicative |

---

## Liên hệ

datasync5ueh@gmail.com
