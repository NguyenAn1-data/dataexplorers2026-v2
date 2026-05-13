<div align="center">

# DATA EXPLORERS 2026 — VÒNG 2

## *From Data to Decision by MEXC Ventures*

---

# BÁO CÁO KỸ THUẬT

## Hệ thống phân tích dữ liệu kinh doanh
## Công ty Cổ phần Xe đạp Thống Nhất

---


**Nhóm:** DataSync

| Họ và tên | Vai trò |
|---|---|
| Nguyễn Đăng Hoàng Ân | Nhóm trưởng |
| Lê Thiên Đức | Thành viên |
| Tạ Ngọc Bảo Ngân | Thành viên |
| Nguyễn Trang Nhật Mai | Thành viên |
| Trần Nguyễn Quỳnh Trâm | Thành viên |

**Liên hệ:** datasync5ueh@gmail.com


</div>

<div style="page-break-after: always;"></div>

## MỤC LỤC

| # | Nội dung | Trang |
|---|---|---|
| | **PHẦN I — GIỚI THIỆU VÀ KIẾN TRÚC HỆ THỐNG** | 3 |
| 1.1 | Bối cảnh và mục tiêu | 3 |
| 1.2 | Kiến trúc tổng thể hệ thống | 3 |
| | **PHẦN II — HẠNG MỤC A: XỬ LÝ ĐƠN HÀNG TỰ ĐỘNG** | 4 |
| 2.1 | Phương án thực hiện và quy trình pipeline | 4 |
| 2.2 | Kiểm tra hợp lệ và xử lý lỗi | 4 |
| 2.3 | Kết quả thực thi và xác minh dữ liệu | 5 |
| | **PHẦN III — HẠNG MỤC B: DASHBOARD VÀ INSIGHTS** | 6 |
| 3.1 | Màn hình 1: Tổng quan kinh doanh | 6 |
| 3.2 | Màn hình 2: Phân tích thời gian | 7 |
| 3.3 | Màn hình 3: Phân tích sản phẩm | 8 |
| 3.4 | Màn hình 4: Phân tích đại lý | 9 |
| 3.5 | Màn hình 5: Phân tích địa lý | 10 |
| 3.6 | Màn hình 6: Trạng thái vận hành | 11 |
| | **PHẦN IV — HẠNG MỤC C: DỰ BÁO NHU CẦU Q2/2026** | 12 |
| 4.1 | Ràng buộc dữ liệu và lựa chọn mô hình | 12 |
| 4.2 | Câu hỏi 1: Dự báo doanh số | 12 |
| 4.3 | Câu hỏi 2: Dự báo màu sắc và SKU bán chậm | 13 |
| 4.4 | Câu hỏi 3: Dự báo hành vi đại lý (BG/NBD) | 13 |
| | **PHẦN V — INSIGHTS KINH DOANH VÀ KHUYẾN NGHỊ** | 14 |
| 5.1 | Bảy insight cốt lõi | 14 |
| 5.2 | Khuyến nghị chiến lược và roadmap | 15 |

<div style="page-break-after: always;"></div>

<h2 style="font-size: 1.8em; font-weight: bold;">PHẦN I — GIỚI THIỆU VÀ KIẾN TRÚC HỆ THỐNG</h2>

### 1.1. Bối cảnh và mục tiêu

Công ty Cổ phần Xe đạp Thống Nhất (Thống Nhất Bike) phân phối hơn 200 SKU thuộc 5 nhóm sản phẩm qua mạng lưới 798 đại lý B2B trên toàn quốc. Hiện tại doanh nghiệp xử lý đơn hàng thủ công qua email/Zalo, chưa có dashboard quản trị, chưa có dự báo nhu cầu và chưa có cảnh báo sớm về hành vi đại lý.

Nhóm DataSync xây dựng giải pháp tích hợp gồm bốn cấu phần: (1) pipeline tự động xử lý 1.132 đơn hàng tháng 3/2026, (2) dashboard phân tích 6 màn hình trên Power BI, (3) hệ thống dự báo Q2/2026 cho ba câu hỏi kinh doanh, và (4) bộ insights kèm khuyến nghị hành động.

### 1.2. Kiến trúc tổng thể hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│  TẦNG 1 — NGUỒN DỮ LIỆU                                     │
│  • PostgreSQL tnbike_db (lịch sử 02/01/2025 – 28/02/2026)   │
│    17.031 dòng giao dịch · 9 bảng · 4 views                 │
│  • 1.132 file .eml + 1.132 file .pdf đính kèm (T3/2026)     │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TẦNG 2 — PIPELINE XỬ LÝ (Python 3.13)                      │
│  parse_eml.py → parse_pdf.py → validate.py → db_writer.py   │
│  Thư viện: email (stdlib), pdfplumber, psycopg2-binary      │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TẦNG 3 — KHO DỮ LIỆU PHÂN TÍCH (PostgreSQL 14)             │
│  Schema tnbike: email_log · sales_order · order_line ·      │
│                 fact_sales · customer · product · ...       │
│  11 views chuyên dụng cho 6 màn hình dashboard              │
│  Schema tnbike_forecast: 8 bảng kết quả dự báo Q2/2026      │
└────────────────────────┬────────────────────────────────────┘
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
┌────────────────────────┐ ┌────────────────────────────────┐
│  TẦNG 4A — BÁO CÁO     │ │  TẦNG 4B — DỰ BÁO              │
│  Power BI Desktop       │ │  Python scripts (9 modules)    │
│  6 màn hình · 30+ KPI   │ │  Backtest 9 phương pháp        │
│  Kết nối trực tiếp PG   │ │  M5 + BG/NBD + Gamma-Gamma     │
└────────────────────────┘ └────────────────────────────────┘
```

**Stack công nghệ:**

| Tầng | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.13, SQL (PostgreSQL 14) |
| Trích xuất | `email` (stdlib), `pdfplumber` |
| Cơ sở dữ liệu | PostgreSQL 14 + psycopg2-binary |
| Phân tích | Pandas, NumPy |
| Dự báo | M5 Seasonal Multiplicative, `lifetimes` (BG/NBD + Gamma-Gamma) |
| Trực quan hoá | Microsoft Power BI Desktop |

<div style="page-break-after: always;"></div>

<h2 style="font-size: 1.8em; font-weight: bold;">PHẦN II — HẠNG MỤC A: XỬ LÝ ĐƠN HÀNG TỰ ĐỘNG</h2>

**Phương án đã chọn:** Phương án A (Email + PDF) 

### 2.1. Phương án thực hiện và quy trình pipeline

Pipeline gồm bốn module Python liên kết tuần tự, mỗi module đảm nhiệm một trách nhiệm rõ ràng theo nguyên tắc Single Responsibility:

```
  ┌───────────────────────────────────────────────────────┐
  │  [1] parse_eml.py    — Đọc 1.132 file .eml            │
  │      • Bóc tách MIME header: From, Subject, Date,     │
  │        Message-ID                                     │
  │      • Phát hiện attachment PDF qua Content-Type      │
  │      • Trích xuất PDF ra thư mục tạm để xử lý         │
  │      • Ghi log vào bảng email_log                     │
  └───────────────────┬───────────────────────────────────┘
                      ▼
  ┌───────────────────────────────────────────────────────┐
  │  [2] parse_pdf.py    — Trích xuất bảng sản phẩm       │
  │      • Đọc PDF bằng pdfplumber.extract_tables()       │
  │      • Phân tích header: số chứng từ, ngày đặt,       │
  │        mã KH, tên đại lý                              │
  │      • Parse bảng chi tiết: mã hàng, tên SP, ĐVT,     │
  │        số lượng, đơn giá, thành tiền                  │
  │      • Đọc footer: tổng đơn hàng (chưa VAT)           │
  └───────────────────┬───────────────────────────────────┘
                      ▼
  ┌───────────────────────────────────────────────────────┐
  │  [3] validate.py     — Kiểm tra tính hợp lệ           │
  │      • Trùng đơn (UNIQUE constraint so_number)        │
  │      • Mã sản phẩm tồn tại trong bảng product         │
  │      • SL > 0, đơn giá > 0                            │
  │      • Đối chiếu sum(line_total) == total_amount      │
  │      • Validate ngày đặt nằm trong T3/2026            │
  └───────────────────┬───────────────────────────────────┘
                      ▼
  ┌───────────────────────────────────────────────────────┐
  │  [4] db_writer.py    — Ghi vào PostgreSQL             │
  │      • Mở transaction → BEGIN                         │
  │      • INSERT email_log (1 row/email)                 │
  │      • INSERT sales_order (header đơn)                │
  │      • INSERT order_line (chi tiết SP)                │
  │      • Trigger tự động cập nhật fact_sales            │
  │      • COMMIT hoặc ROLLBACK nếu lỗi                   │
  └───────────────────────────────────────────────────────┘
```

### 2.2. Kiểm tra hợp lệ và xử lý lỗi

Pipeline triển khai năm tầng kiểm tra trước khi ghi DB:

| Tầng | Loại kiểm tra | Hành động khi lỗi |
|---|---|---|
| 1 | Kết nối DB còn sống | Dừng pipeline, ghi log critical |
| 2 | File .eml hợp lệ (parse được MIME) | Đẩy vào `errors_<timestamp>.json` |
| 3 | PDF trích xuất được bảng | Đẩy vào error log, không ghi DB |
| 4 | Mã sản phẩm/đại lý tồn tại | Tự động đăng ký mới (`fix_missing_data.py`) |
| 5 | Số học khớp (sum line == total) | Ghi cảnh báo, vẫn cho phép ghi nếu lệch < 1.000đ |

Mọi lỗi đều được ghi vào file JSON kèm timestamp tại `pipeline/logs/errors_YYYYMMDD_HHMMSS.json` để truy vết.

<div style="page-break-after: always;"></div>

### 2.3. Kết quả thực thi và xác minh dữ liệu

**Output terminal khi chạy `python main.py`:**

```
PS D:\Data explore vòng 2\pipeline> python main.py

================================================================
  THỐNG NHẤT BIKE — PIPELINE XỬ LÝ ĐƠN HÀNG T3/2026
================================================================
[INFO] Kết nối PostgreSQL tnbike_db ............ OK
[INFO] Quét thư mục Emails: tìm thấy 1.132 file .eml
[INFO] Bắt đầu xử lý...

Processing emails: 100%|██████████████████████| 1132/1132 [09:10<00:00]

================================================================
  KẾT QUẢ XỬ LÝ
================================================================
  SUCCESS         : 1.132   (100,00%)
  DUPLICATE       :     0
  ERROR (parse)   :     0
  ERROR (validate):     0
  ERROR (db)      :     0
  ----------------------------------------------------------------
  fact_sales rows inserted : 8.721
  Tổng doanh thu T3/2026    : 40.692.350.000 VND  (≈ 40,69 tỷ)
  Thời gian xử lý           : 550,2 giây (9 phút 10 giây)
  Tốc độ trung bình         : 0,486 giây/đơn
================================================================
```

**Xác minh trên PostgreSQL sau khi pipeline chạy xong:**

```sql
SELECT 'email_log T3/2026'   AS bang, COUNT(*) AS so_dong
FROM tnbike.email_log
UNION ALL
SELECT 'sales_order T3/2026', COUNT(*)
FROM tnbike.sales_order
WHERE order_date >= '2026-03-01' AND order_date < '2026-04-01'
UNION ALL
SELECT 'order_line T3/2026', COUNT(*)
FROM tnbike.order_line ol
JOIN tnbike.sales_order so USING(order_id)
WHERE so.order_date >= '2026-03-01' AND so.order_date < '2026-04-01'
UNION ALL
SELECT 'fact_sales T3/2026', COUNT(*)
FROM tnbike.fact_sales
WHERE fiscal_year = 2026 AND fiscal_month = 3;
```

**Kết quả truy vấn:**

```
         bang          | so_dong
-----------------------+---------
 email_log T3/2026     |    1132
 sales_order T3/2026   |    1132
 order_line T3/2026    |    8721
 fact_sales T3/2026    |    8721
(4 rows)
```

**Bảng tổng kết kết quả Hạng mục A:**

| Chỉ số | Giá trị | Ghi chú |
|---|---|---|
| Tỷ lệ xử lý thành công | **100% (1.132/1.132)** | Không có đơn nào lỗi |
| Số dòng sản phẩm trích xuất | **8.721** | Trung bình 7,7 dòng/đơn |
| Tổng doanh thu T3/2026 nhập vào | **40,69 tỷ VND** | Khớp với tổng PDF |
| Thời gian xử lý toàn bộ | **9 phút 10 giây** | Trên máy CPU thông thường |
| Tốc độ trung bình | **0,49 giây/đơn** | Bao gồm đọc PDF + ghi DB |
| Số bảng được cập nhật | **4** | email_log, sales_order, order_line, fact_sales |

Pipeline đạt yêu cầu của Phương án A: toàn bộ 1.132 đơn hàng T3/2026 đã có mặt tự động trong database, sẵn sàng cho Hạng mục B và C khai thác.

<div style="page-break-after: always;"></div>

<h2 style="font-size: 1.8em; font-weight: bold;">PHẦN III — HẠNG MỤC B: DASHBOARD VÀ INSIGHTS</h2>

Dashboard xây dựng trên Microsoft Power BI Desktop, kết nối trực tiếp PostgreSQL `tnbike_db`, sử dụng 11 view chuyên dụng để tách logic phân tích khỏi tầng trực quan hoá. Sáu màn hình bám sát yêu cầu B.4 của đề thi.

### 3.1. Màn hình 1 — Tổng quan kinh doanh

![Màn hình 1 — Tổng quan kinh doanh](images/anh_man_1_tong_quan.png)

Bố cục: 6 thẻ KPI hàng đầu + line chart xu hướng + donut 3 miền + bar nhóm SP + funnel pipeline T3/2026.

| KPI | Giá trị | So với Q1/2025 |
|---|---|---|
| Tổng doanh thu | **81,22 tỷ VND** | ▲ 188,85% |
| Số đơn hàng | **2.066** | ▲ 198,12% |
| Số lượng bán | **50.552** | ▲ 135,39% |
| Đại lý hoạt động | **517 / 798 (64,8%)** | — |
| Số dòng SP/đơn | 8,88 | — |
| Doanh thu TB/đơn | 39,31 triệu | — |

Line chart T1/2025 → T3/2026 cho thấy đỉnh T3/2026 đạt 40,7 tỷ — gấp đôi T3/2025 (18,6 tỷ). Donut 3 miền: Bắc 69,2% — Trung 18,89% — slice "Trống" 7% (97 đại lý chưa gắn tỉnh). CITYBIKE_P dẫn đầu nhóm SP với 54,3 tỷ. Funnel T3/2026: 1.132 → 1.132 → 1.132 không hao hụt.

### 3.2. Màn hình 2 — Phân tích thời gian

![Màn hình 2 — Phân tích thời gian](images/anh_man_2_thoi_gian.png)

| KPI | Giá trị | Ý nghĩa |
|---|---|---|
| YoY Q1/2026 vs Q1/2025 | **+188,85%** | +51 tỷ |
| MoM T3/2026 vs T2/2026 | **+109,9%** | Hơn gấp đôi tháng trước |
| YoY% T3/2026 vs T3/2025 | **+119%** | Cao hơn TB quý |
| % DT T3 trong năm 2026 | **50,10%** | T3 đóng góp một nửa Q1+T3 |

Cả 2025 lẫn 2026 đều có T3 là đỉnh, nhưng baseline 2026 cao gấp 6–7 lần (T1: 3 → 21 tỷ, T2: 6 → 19 tỷ, T3: 19 → 41 tỷ). T2/2026 giảm −8% do Tết Bính Ngọ 17/02, T3/2026 +110% là hiệu ứng phục hồi sau Tết. Seasonal Index T1/T2/T3: 34/68/198 (2025) → 78/72/150 (2026) — chỉ số đỉnh mùa T3 **co lại** (198 → 150), nhu cầu phân bổ đều hơn. YoY% T3 theo nhóm: SPORTBIKE_A +201%, CITYBIKE_P +139%, KIDBIKE_2 +94%, KIDBIKE_1 +52%, SPORTBIKE_S +34%.

### 3.3. Màn hình 3 — Phân tích sản phẩm

![Màn hình 3 — Phân tích sản phẩm](images/anh_man_3_san_pham.png)

5/5 nhóm SP hoạt động · 71/83 dòng xe có giao dịch · 214/265 SKU bán được · Top 10 dòng xe chiếm **62,1%** doanh thu.

**Cấp 1 — Nhóm:** CITYBIKE_P chiếm 66,87% doanh thu (54,31 tỷ); bốn nhóm còn lại chia 33%.
**Cấp 2 — Dòng xe:** Top bán chạy Q1/2026 — Xe New 26 (10,5 tỷ), Xe LD 26 (8,7), Xe New 24 (6,7), Xe GN 06-24 2.0 (4,3), Xe LD 24-01 2023 (4,2), Xe MTB SPD 27.5 (3,9). Top 5 tăng trưởng YoY (baseline ≥ 100 triệu): Xe Super 26 **+517,8%**, Xe GN 06-24 2.0 +350,8%, Xe MTB SPD 27.5 +346,8%, Xe Nữ +274,8%, Xe Bunny 16 +271,0%.
**Cấp 3 — Màu:** Heatmap Top 10 dòng × Top 15 màu cho thấy Kem thống trị Xe New 26 và nhiều dòng top khác.

**Ma trận BCG (83 dòng xe):**

| Phân loại | Số dòng | Hành động |
|---|---|---|
| **Star** | 5 (Xe New 26, New 24, LD 26, LD 24-01 2023, GN 06-24 2.0) | Ưu tiên đầu tư |
| Question Mark | 30 | Đánh giá chọn lọc |
| Dog | 48 | Cắt giảm / EOL |

### 3.4. Màn hình 4 — Phân tích đại lý

![Màn hình 4 — Phân tích đại lý](images/anh_man_4_dai_ly.png)

| KPI | Giá trị |
|---|---|
| Đại lý hoạt động Q1/2026 | **517 / 798 (64,8%)** |
| VIP Champions | 191 (60,79% DT) |
| Top 20% tạo ra | **68,31%** DT |
| % ĐL chiếm 80% DT | 32,8% (Pareto lệch nặng) |
| ĐL có tín hiệu rời bỏ | **292** (−18,60 tỷ vs Q1/2025) |
| Doanh thu TB/ĐL | 157,09 triệu |

Scatter RFM phân bố bimodal: cluster Champions 0–100 ngày tách biệt cluster Lost 300–450 ngày. Donut RFM: Champions 60,79% — Loyal 18,33% — At Risk 12,27% — Lost 5,57%. Pareto: Top 5 ≈ 25% DT, Top 35 ≈ 60% DT, Top 160 (20%) = 68,31% DT. Top 1 — Bình Minh ~9,5 tỷ (8,27% toàn hệ thống), gap lớn so với #2. Bảng churn 292 đại lý gồm các công ty Quảng Vinh, Toàn Thắng, Thuý Tiên, Vĩnh Phát… nhiều đại lý YoY −100%. Theo vùng: Miền Nam có tỷ lệ Inactive 42,86% ngang ngửa Growing 42,86% — vùng có rủi ro cao nhất.

### 3.5. Màn hình 5 — Phân tích địa lý

![Màn hình 5 — Phân tích địa lý](images/anh_man_5_dia_ly.png)

Độ phủ **38/63 tỉnh** · Top 5 chiếm **62,7%** · Hà Nội dẫn đầu **36,5%** · **9 tỉnh** YoY > 200%. Cơ cấu vùng: Bắc 74,41% — Trung 20,31% — Nam 5,28%. (Lưu ý: 97 đại lý chưa gắn tỉnh ≈ 5,68 tỷ không hiển thị.)

**Top 10 tỉnh Q1/2026 (tỷ VND):** Hà Nội 27,5 (36,5%) — Thanh Hoá 6,9 — Ninh Bình 5,0 — Hải Phòng 4,0 — Nghệ An 3,9 — HCM 3,9 — Hưng Yên 3,4 — Phú Thọ 3,1 — Bắc Ninh 3,1 — Bắc Giang 2,2. Mốc 80% DT rơi vào tỉnh thứ 3–4 (Ninh Bình ↔ Hải Phòng).

**Vành đai Hà Nội bùng nổ YoY (baseline ≥ 0,3 tỷ):** Ninh Bình **+831%**, Phú Thọ +778%, Hải Phòng +560%, Bắc Ninh +483%, Hà Tĩnh +328%, Quảng Ninh +321%, Thái Nguyên +311%, Hưng Yên +239%, Thanh Hoá +228%. Hai tỉnh giảm: Nam Định −100% (ngừng hoàn toàn), Vĩnh Phúc −41%. Miền Nam chỉ 7 đại lý nhưng ARPC 570 triệu/quý — gấp 5,6× Miền Bắc (101 triệu), là thị trường trắng cần ưu tiên mở rộng.

### 3.6. Màn hình 6 — Trạng thái vận hành

![Màn hình 6 — Trạng thái vận hành](images/anh_man_6_van_hanh.png)

| KPI | Giá trị | Mục tiêu | Đánh giá |
|---|---|---|---|
| Email xử lý / DB / Tỉ lệ | **1.132 / 1.132 / 100%** | ≥ 99% | Vượt |
| Số đơn lỗi | **0** | ≤ 1% | Vượt |
| Doanh thu nhập vào | **40,69 tỷ** | — | Khớp PDF |
| Thời gian chạy | 9,17 phút | < 15 phút | Đạt |

Phễu 5 bước (Email → Parse → Khớp ĐL → Ghi sales_order → Ghi order_line) không hao hụt, kết thúc 8.721 dòng (TB 7,7 dòng/đơn). Phân bố nhận email lệch về cuối tháng (đỉnh 20–28/03), cao điểm 09h–14h, Thứ Tư dẫn đầu 243 emails; T7/CN gần như không có. Nhật ký 1.132 dòng đều **SUCCESS**, lead time 91–97 giây/đơn. Pipeline đạt chuẩn production: 0 lỗi, 0 can thiệp thủ công.

<div style="page-break-after: always;"></div>

<h2 style="font-size: 1.8em; font-weight: bold;">PHẦN IV — HẠNG MỤC C: DỰ BÁO NHU CẦU Q2/2026</h2>

### 4.1. Ràng buộc dữ liệu và lựa chọn mô hình

Sau khi Hạng mục A hoàn thành, database có 25.752 dòng giao dịch / 2.759 đơn / 798 đại lý / 265 SKU. Tuy nhiên phạm vi thời gian thực tế chỉ gồm **6 tháng có dữ liệu** (Q1/2025 và Q1/2026), 9 tháng giữa Q2/2025–Q4/2025 hoàn toàn trống.

| Ràng buộc | Hệ quả |
|---|---|
| 0/265 SKU có ≥ 12 tháng lịch sử | Không fit được SARIMA/Prophet theo SKU |
| 74% đại lý có < 4 đơn | Quá sparse cho time-series theo đại lý |
| Q2/2026 không có precedent năm trước | Không tính được seasonal index Q2 |
| 5 series × 5 tháng training | LightGBM/Deep Learning dễ overfit |

→ Lựa chọn ưu tiên: **mô hình đơn giản, robust, validate cẩn thận trên holdout T3/2026** (đã biết actual = 40,69 tỷ).

### 4.2. Câu hỏi 1 — Dự báo doanh số Q2/2026

**Quy trình backtest:** Train trên {T1, T2, T3/2025, T1, T2/2026}, holdout T3/2026. Đánh giá 9 phương pháp:

| Mã | Phương pháp | Sai số tổng | Group WAPE |
|---|---|---|---|
| M1 | Naive last (T3 = T2/26) | −52,4% | 52,4% |
| M2 | Naive avg (T3 = avg(T1,T2)/26) | −50,2% | 50,2% |
| M3 | YoY-T2 ratio | +39,7% | 44,3% |
| M4 | YoY-avg ratio | +94,1% | 97,6% |
| **M5** | **Seasonal Multiplicative** | **−1,3%** | **4,4%** |
| M6 | Share preservation | +94,1% | 97,6% |
| M7 | Damped YoY (0.6) | +8,8% | 9,4% |
| M8 | Median ensemble | +19,2% | 21,0% |
| M9 | LightGBM | — | 45,3% |

**M5 thắng tuyệt đối** với WAPE total 1,3% — chính xác cấp production cho cấp tổng + nhóm.

**Logic M5:** Coi mỗi tháng Q1/2025 là một seasonal index so với Q1-mean (T3/25 ≈ 1,985 lần Q1-mean). Áp index lên 2026 với "level" tính từ Jan + Feb/2026 → predict T3/26.

**Forecast Q2/2026 (sau khi M5 validated):**

Giả định: Mar/2026 là phục hồi sau Tết, không phải mức bình thường mới → Q2 quay về baseline avg(T1+T2)/26 = 20,25 tỷ, có MoM growth nhẹ phản ánh xu hướng (Apr ×1,05; May ×1,07; Jun ×1,10). Sensitivity ±15%.

| Tháng | Pessimistic | **Base** | Optimistic | Số đơn dự kiến | SL dự kiến |
|---|---|---|---|---|---|
| Apr/2026 | 18,08 | **21,28** | 24,47 | 491 | 13.159 |
| May/2026 | 18,43 | **21,68** | 24,93 | 500 | 13.410 |
| Jun/2026 | 18,94 | **22,29** | 25,63 | 514 | 13.785 |
| **Q2 Tổng** | **55,5** | **65,2** | **75,0** | **1.505** | **40.354** |

**Phân bổ theo 5 nhóm sản phẩm (kịch bản Base):**

| Nhóm | Q2 Revenue (tỷ) | % share |
|---|---|---|
| Xe phổ thông (CITYBIKE_P) | 44,41 | 68,1% |
| Xe trẻ em nhóm 1 (KIDBIKE_1) | 6,56 | 10,1% |
| Xe thể thao nhôm (SPORTBIKE_A) | 5,90 | 9,0% |
| Xe trẻ em nhóm 2 (KIDBIKE_2) | 4,21 | 6,5% |
| Xe thể thao thép (SPORTBIKE_S) | 4,17 | 6,4% |

**Trả lời câu hỏi "Sản phẩm nào sẽ bán được?":** Q2/2026 dự kiến đạt **65,2 tỷ VND** (dải 55–75 tỷ), giảm so với T3/2026 nhưng tăng nhẹ qua từng tháng (Apr 21,3 → May 21,7 → Jun 22,3 tỷ). **Xe phổ thông (CITYBIKE_P) tiếp tục là trụ cột bán chạy nhất** với 44,4 tỷ chiếm 68,1% doanh thu quý, kế đến là KIDBIKE_1 (6,6 tỷ), SPORTBIKE_A (5,9 tỷ), KIDBIKE_2 (4,2 tỷ) và SPORTBIKE_S (4,2 tỷ). Ở cấp SKU, **Top 20 mẫu xe bán chạy dự kiến** tập trung ở các dòng Xe New 26, Xe LD 26, Xe New 24, Xe GN 06-24 2.0 và Xe MTB SPD 27.5 — đây cũng chính là các dòng đã đạt vị trí Star trong ma trận BCG Q1/2026.

<div style="page-break-after: always;"></div>

### 4.3. Câu hỏi 2 — Dự báo màu sắc và SKU bán chậm

**Phương pháp:** Tính share doanh thu của từng màu trong Q1 mỗi năm, đo chênh lệch điểm phần trăm (Q1/26 − Q1/25). Bổ sung rule-based classifier cho SKU bán chậm.

**Top 5 màu tăng share & Top 5 màu giảm share:**

| Top tăng (điểm %) | Top giảm (điểm %) |
|---|---|
| Kem **+4,57** | Xanh dương **−5,15** |
| đen (lowercase) +4,18 | Đen (uppercase) −2,54 |
| Pastel Xanh +2,43 | Coban −2,16 |
| Hồng +2,14 | Café/nâu −1,42 |
| Ghi +2,00 | Xanh mint −0,50 |

**Lưu ý chất lượng dữ liệu:** "Đen" và "đen" được lưu như hai màu khác nhau — cần chuẩn hoá trong ERP để báo cáo chính xác.

**Dự báo share màu Q2/2026 (per group, top màu):**
- CITYBIKE_P (44,4 tỷ): Kem 22% — Ghi 10% — đen 8% — Trắng 8% — Đen 7%
- KIDBIKE_1 (6,6 tỷ): Hồng 26% — Xanh 16% — Kem 12% — Đen 11%
- KIDBIKE_2 (4,2 tỷ): Hồng 31% — Xanh dương 25% — Ghi 14%
- SPORTBIKE_A (5,9 tỷ): Đen 41% — Ghi 19% — Xanh 19%
- SPORTBIKE_S (4,2 tỷ): ghi 21% — xanh 17% — HP 16%

**Phát hiện SKU bán chậm:** Rule-based với 3 tiêu chí (OR):

| Tiêu chí | Định nghĩa | Số SKU |
|---|---|---|
| `t3_drop` | T3/26 qty < 30% trung bình T1+T2/26 | 14 |
| `dead_in_2026` | Active 2025 nhưng zero Q1/26 | 43 |
| `pred_drop` | Q2 forecast < 30% Q1/26 actual | 25 |
| **Tổng (sau khi loại trùng)** | **82/247 SKU (33%)** | |

**Trả lời câu hỏi "Màu sắc/Cải tiến nào sẽ được ưa chuộng?":** Quý 2/2026 dự kiến tiếp tục đà dịch chuyển thị hiếu đã thấy rõ ở Q1/2026 — **nhóm màu trung tính và pastel (Kem, đen, Pastel Xanh, Hồng, Ghi) sẽ tăng share mạnh nhất**, trong đó Kem là màu dẫn đầu xu hướng (+4,57 điểm phần trăm) và xuất hiện ở 4/20 vị trí đầu của Top 20 SKU bán chạy. Ngược lại, **các màu Xanh dương, Đen (uppercase), Coban và Café/nâu sẽ tiếp tục mất share** (giảm từ −1,4 đến −5,2 điểm %) — cần cân nhắc giảm sản xuất hoặc refresh thiết kế. Về SKU bán chậm, **82/247 SKU (33%) có dấu hiệu nhu cầu giảm hoặc đã chết** trong Q1/2026, gồm 43 SKU không có giao dịch nào trong quý, 14 SKU giảm mạnh ở T3/26 và 25 SKU dự báo Q2 giảm > 70% so Q1/26 — đây là danh mục ưu tiên đưa vào quy trình EOL (End-of-life).

### 4.4. Câu hỏi 3 — Dự báo hành vi đại lý (BG/NBD)

**Lý do chọn BG/NBD:** 798 đại lý với 74% có < 4 đơn → quá sparse cho time-series. BG/NBD (Beta-Geometric Negative Binomial Distribution) là mô hình probabilistic kinh điển cho "buy-till-you-die", chỉ cần dữ liệu RFM (Recency, Frequency, T), kết hợp Gamma-Gamma để ước lượng giá trị tiền tệ → CLV.

**Mô hình toán (fit MLE trên transaction data toàn 798 đại lý):**
- Mỗi đại lý có Poisson purchase rate λ ~ Gamma(r=0,365, α=11,55)
- Sau mỗi giao dịch, xác suất ngưng p ~ Beta(a=0,209, b=0,662)

**Predictions cốt lõi:**
- **E[purchases trong 30 ngày]** — kỳ vọng số đơn 30 ngày tới
- **P(alive)** — xác suất đại lý vẫn còn hoạt động
- **CLV 90 ngày** — kết hợp BG × Gamma-Gamma

**Kết quả phân tier:**

| Tier | Số đại lý | Avg P_alive | Avg P_order_30d | Exp Q2 revenue (tỷ) |
|---|---|---|---|---|
| 1_Champion | 65 | 0,95 | 0,82 | **28,5** |
| 2_Loyal | 202 | 0,99 | 0,12 | 4,8 |
| 3_At_Risk | 531 | 0,69 | 0,30 | 27,0 |

**Cảnh báo churn:** 116 đại lý có P_alive < 0,4 (14,5% tổng), exposure ~3 tỷ Q2.

**Top 5 churn risk ưu tiên can thiệp:**

| Customer | P_alive | P(order 30d) | Exp Q2 rev (triệu) |
|---|---|---|---|
| KH-00491 | 0,218 | 0,108 | 115,9 |
| KH-00551 | 0,314 | 0,155 | 80,6 |
| KH-00461 | 0,379 | 0,178 | 73,3 |
| KH-00425 | 0,393 | 0,178 | 46,2 |
| KH-00644 | 0,275 | 0,164 | 18,2 |

**Trả lời câu hỏi "Đại lý nào sẽ mua hàng?":** Trong 30 ngày tới, **65 đại lý nhóm Champion là nhóm chắc chắn sẽ tiếp tục mua hàng nhất** với xác suất đặt đơn trung bình **0,82** và P_alive 0,95 — đây là nhóm cần ưu tiên chăm sóc cao nhất vì đóng góp tới **28,5 tỷ ≈ 47% doanh thu Q2 dự báo**. Nhóm 202 đại lý Loyal có P_alive gần như tuyệt đối (0,99) nhưng tần suất mua thấp (P_order_30d = 0,12) → cần kích hoạt để nâng tần suất. Ngược lại, **116 đại lý (14,5% tổng số) có P_alive < 0,4 đang nằm trong vùng nguy cơ rời bỏ** với exposure ~3 tỷ VND Q2; trong đó **Top 5 ưu tiên can thiệp là KH-00491, KH-00551, KH-00461, KH-00425, KH-00644** — tổng exposure 334 triệu nhưng có lịch sử giá trị đơn 50–200 triệu/đơn, cần sales team gọi điện trực tiếp trong vòng 14 ngày để giữ chân.

<div style="page-break-after: always;"></div>

<h2 style="font-size: 1.8em; font-weight: bold;">PHẦN V — INSIGHTS KINH DOANH VÀ KHUYẾN NGHỊ</h2>

### 5.1. Bảy insight cốt lõi

Mỗi insight được trình bày theo cấu trúc ba phần đề thi yêu cầu: **Phát hiện từ dữ liệu → Ý nghĩa kinh doanh → Khuyến nghị hành động**.

**Insight 1 — Spike T3/2026 là phục hồi sau Tết, KHÔNG phải mức bình thường mới.**
*Phát hiện:* Doanh thu T3/26 đạt 40,7 tỷ — gấp đôi baseline pre-Tết (avg T1+T2/26 = 20,2 tỷ). Tết Bính Ngọ rơi vào 17/02/2026, T2/26 bị nén do nghỉ Tết, T3/26 bùng nổ là hiệu ứng đơn dồn lại.
*Ý nghĩa:* Nếu extrapolate Q2 dựa trên Mar/26, doanh nghiệp sẽ over-produce gấp đôi nhu cầu thực tế.
*Khuyến nghị:* Plan production Q2/2026 ở mức 65 tỷ tổng quý (dải 55–75 tỷ). Đẩy mạnh sản xuất từ T11–T12 hằng năm để chuẩn bị Tết, không phải Q2.

**Insight 2 — Concentration risk cực cao: 65 Champion đại lý (8,1%) chiếm 47% doanh thu Q2 dự báo.**
*Phát hiện:* BG/NBD phân loại 65 đại lý Champion đóng góp 28,5 tỷ ≈ 47% Q2 dự kiến, trong khi 531 At-Risk cùng nhau chỉ ngang ngửa.
*Ý nghĩa:* Mất 1 trong Top 10 Champion → doanh thu Q2 giảm ngay 2–5%. Rủi ro Pareto cấp 1.
*Khuyến nghị:* (1) Lập Champion Retention Program — gán account manager riêng cho 65 đại lý này; (2) Diversify danh mục — target onboard 20–30 đại lý mới hạng B → A trong Q2/2026.

**Insight 3 — 116 đại lý (14,5%) có nguy cơ rời bỏ — exposure tới 3 tỷ Q2.**
*Phát hiện:* BG/NBD flag `P_alive < 0.4` cho 116 đại lý. Top 5 churn risk có giá trị đơn lịch sử 50–200 triệu/đơn.
*Ý nghĩa:* Lifetime value lớn nhưng đang im lặng. Không can thiệp → Q2 mất 3–5 tỷ.
*Khuyến nghị:* (1) Sales team gọi điện/Zalo trực tiếp Top 5 churn trong 14 ngày; (2) Khảo sát nguyên nhân (giá, sản phẩm, dịch vụ); (3) Cấp khuyến mãi/credit term ưu đãi đặc biệt nếu cần.

**Insight 4 — Màu Kem dẫn đầu xu hướng (+4,6 điểm % share Q1/25 → Q1/26).**
*Phát hiện:* Top 5 màu tăng share: Kem (+4,6pp), đen (+4,2pp), Pastel Xanh (+2,4pp), Hồng (+2,1pp), Ghi (+2,0pp). Top giảm: Xanh dương (−5,1pp), Đen (−2,5pp). Trong Top 20 SKU dự báo Q2/26, 4/20 SKU màu Kem (chiếm 4 vị trí đầu).
*Ý nghĩa:* Shift thị hiếu rõ ràng — xảy ra ở cả Q1/25 và Q1/26 cùng chiều, không phải nhiễu. Màu Xanh dương rớt mạnh báo hiệu cần đổi mới.
*Khuyến nghị:* (1) Tăng sản xuất SKU màu Kem +30–40% cho Q2, ưu tiên Xe New 26, LD 26, LD 24; (2) Giảm/refresh SKU Xanh dương trong KIDBIKE_2, đề xuất chuyển sang Pastel Xanh; (3) Chuẩn hoá tên màu trong ERP ("Đen" vs "đen").

**Insight 5 — 82/247 SKU (33%) có dấu hiệu bán chậm hoặc đã chết.**
*Phát hiện:* 43 SKU đã chết Q1/2026 (active 2025 nhưng zero Q1/26), 14 SKU giảm mạnh T3/26 (qty < 30% trung bình T1+T2), 25 SKU dự báo Q2 giảm > 70%.
*Ý nghĩa:* Danh mục xoay vòng nhanh. 43 SKU chết chiếm storage/working capital không sinh doanh thu (~2–3 tỷ tồn kho).
*Khuyến nghị:* (1) EOL ngay 43 SKU không có giao dịch 6 tháng — liquidation hoặc destruction; (2) Monitor 14 SKU `t3_drop` trong 30 ngày, nếu T4 tiếp tục giảm → đưa vào EOL pipeline; (3) Quy trình mới: SKU không có giao dịch 90 ngày → auto-flag review.

<div style="page-break-after: always;"></div>

**Insight 6 — CITYBIKE_P chiếm 68% doanh thu Q2 — rủi ro tập trung sản phẩm.**
*Phát hiện:* Nhóm Xe phổ thông dự kiến đóng góp 44,4/65,2 = 68% Q2/2026. Bốn nhóm còn lại chia nhau 32%.
*Ý nghĩa:* Bất kỳ shock nào lên CITYBIKE_P (đối thủ, regulation, supply chain) đều ảnh hưởng toàn công ty. Các nhóm SPORTBIKE và KIDBIKE chưa được phát triển đúng tiềm năng.
*Khuyến nghị:* (1) Đặt OKR Q3–Q4/2026 nâng share KIDBIKE_2 từ 6,4% lên 10%; (2) Đầu tư marketing cho SPORTBIKE_A (phân khúc cao cấp, biên LN tốt); (3) Triển khai bundling KIDBIKE + CITYBIKE để cross-sell qua đại lý.

**Insight 7 — Vành đai Hà Nội bùng nổ, Miền Nam là thị trường trắng.**
*Phát hiện:* (1) Hà Nội đơn lẻ chiếm 36,5% doanh thu; (2) Top 5 tỉnh = 62,7%; (3) Vành đai Hà Nội tăng 400–800% YoY (Ninh Bình +831%, Phú Thọ +778%, Hải Phòng +560%, Bắc Ninh +483%); (4) Miền Nam chỉ 7 đại lý nhưng ARPC 570 triệu/Q1 (gấp 5,6× Miền Bắc 101 triệu).
*Ý nghĩa:* Concentration risk địa lý cực cao — mất Hà Nội mất 1/3 doanh thu. Đồng thời vành đai HN cho thấy hiệu ứng tràn dòng — nhu cầu thực tế đang lan rộng. Miền Nam có hiệu suất tốt nhưng chưa khai thác.
*Khuyến nghị:* (1) Mở 5–8 đại lý mới ở Ninh Bình, Phú Thọ, Hải Phòng, Bắc Ninh trong Q2/2026 để đón nhu cầu tràn; (2) Triển khai kế hoạch Nam tiến — target onboard 20–30 NPP mới tại HCM + ĐBSCL trong nửa cuối 2026; (3) Đa dạng hoá để giảm tỷ trọng Hà Nội xuống dưới 30% trong 12 tháng.

### 5.2. Khuyến nghị chiến lược và roadmap

**Ưu tiên hành động ngắn hạn (Q2/2026):**

| # | Hành động | Bộ phận chịu trách nhiệm | Thời hạn |
|---|---|---|---|
| 1 | Plan production Q2 theo dải 55–75 tỷ | Sản xuất + Kinh doanh | 30/5/2026 |
| 2 | Gọi điện Top 5 churn risk | Sales | 14 ngày |
| 3 | Tăng sản xuất SKU màu Kem +30–40% | Kế hoạch sản xuất | 15/4/2026 |
| 4 | EOL 43 SKU chết | Quản lý sản phẩm | 30/4/2026 |
| 5 | Mở 5–8 đại lý vành đai Hà Nội | Phát triển kênh | Q2/2026 |
| 6 | Khởi động Champion Retention Program | Sales + CRM | 1/5/2026 |

**Roadmap nâng cấp hệ thống khi có thêm dữ liệu:**

| Khi nào | Hành động kỹ thuật |
|---|---|
| Có dữ liệu Q2/Q3/Q4 2025 | Re-validate M5 bằng walk-forward backtest; fit Prophet/SARIMA seasonal năm |
| Có dữ liệu 24+ tháng | Train LightGBM với lag-12 features cho dự báo per-SKU |
| Khi cần dealer-level | Cox PH survival model cho time-to-next-order |
| Vận hành liên tục | Triển khai M5 forecast monthly rolling — chạy đầu mỗi tháng để cập nhật |
| Cải thiện chất lượng | Chuẩn hoá tên màu trong ERP, gắn 97 đại lý "Trống" với tỉnh |

**Hạn chế đã nhận diện của giải pháp hiện tại:**
1. Q2/2026 không có precedent năm trước → model dựa trên assumption "Q2 = baseline pre-Tết + trend". Cần monitoring rolling.
2. BG/NBD giả định thị trường tĩnh — nếu doanh nghiệp tung campaign lớn, cần bổ sung uplift model.
3. Color share dự báo dựa trên trend Q1/25 → Q1/26. Khi launch sản phẩm mới với màu mới → cần điều chỉnh thủ công.

**Kết luận:** Giải pháp đạt mục tiêu đề bài ở cả ba hạng mục kỹ thuật A/B/C. Pipeline xử lý 100% đơn T3/2026 không lỗi; dashboard 6 màn hình bao phủ đầy đủ các chiều phân tích bắt buộc và hơn 30 KPI; mô hình dự báo M5 đạt độ chính xác production-grade (WAPE 1,3% total trên backtest T3/26). Bộ 7 insight kinh doanh kèm khuyến nghị hành động cụ thể đã chuyển hoá phân tích thành các quyết định khả thi, sẵn sàng triển khai ngay trong Q2/2026.

---

*— Hết Báo cáo kỹ thuật — Nhóm DataSync, Học viện Chính sách và Phát triển —*
