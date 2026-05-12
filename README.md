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

### Tóm tắt
- **Model chính**: Seasonal Multiplicative (M5) — chọn qua backtest T3/2026, WAPE total **1,3%**, group **4,4%**
- **3 câu hỏi đề bài**:
  - Câu 1 (sản phẩm): forecast Apr/May/Jun cho total + 5 nhóm + top-20 SKU, Q2 ≈ **65,2 tỷ** (dải 55,5 – 75,0)
  - Câu 2 (màu): share màu Q2/26 + 82 SKU bán chậm
  - Câu 3 (đại lý): BG/NBD cho 798 đại lý → **65 Champion, 116 churn risk**
- **Output**: 8 bảng forecast trong schema `tnbike_forecast`

### Cách chạy
```bash
python forecast/01_build_dataset.py
python forecast/02_backtest_total_group.py
python forecast/03_backtest_sku.py
python forecast/05_forecast_q2_sales.py
python forecast/06_forecast_q2_color.py
python forecast/07_dealer_forecast.py
python forecast/08_write_forecasts_to_db.py
python forecast/09_generate_insights.py
```

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
