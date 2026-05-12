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
 validate.py         ← Kiểm tra hợp lệ: trùng lặp, ngày tháng, mã hàng, số lượng, thành tiền
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

### Yêu cầu hệ thống
- Python 3.11+
- PostgreSQL 14+
- RAM tối thiểu 4GB

### Bước 1: Clone repo
```bash
git clone https://github.com/NguyenAn1-data/dataexplorers2026-v2.git
cd dataexplorers2026-v2
```

### Bước 2: Cài thư viện Python
```bash
pip install -r pipeline/requirements.txt
```

### Bước 3: Cấu hình database
```bash
copy pipeline\config.example.py pipeline\config.py
# Mở config.py và điền thông tin kết nối PostgreSQL của bạn
```

### Bước 4: Khởi tạo database
```bash
cd pipeline
python setup_db.py
```
> Tạo database `tnbike_db`, import schema và dữ liệu lịch sử 2025-T2/2026.

### Bước 5: Chạy pipeline

**Lưu ý:** Cần có thư mục chứa 1.132 file `.eml` — cập nhật đường dẫn trong `config.py`.

```bash
python main.py
```

Output mẫu:
```
Processing emails: 100%|████████████████| 1132/1132 [04:23<00:00]
SUCCESS: 1132 | DUPLICATE: 0 | ERROR: 0
fact_sales: 8721 rows inserted
```

---

## Cấu trúc thư mục

```
dataexplorers2026-v2/
├── README.md
├── .gitignore
├── pipeline/
│   ├── main.py              # Điều phối toàn bộ pipeline
│   ├── parse_eml.py         # Parser file .eml
│   ├── parse_pdf.py         # Parser PDF bằng pdfplumber
│   ├── validate.py          # Kiểm tra tính hợp lệ dữ liệu
│   ├── db_writer.py         # Ghi vào PostgreSQL
│   ├── setup_db.py          # Khởi tạo database lần đầu
│   ├── fix_missing_data.py  # Đăng ký KH/SP mới phát hiện
│   ├── fix_all_remaining.py # Xử lý hàng loạt lỗi còn lại
│   ├── fix_final.py         # Fix đặc biệt SP có mã đặc biệt
│   ├── config.example.py    # Template cấu hình (copy → config.py)
│   └── requirements.txt
└── Database/
    ├── 01_create_tables.sql  # Schema 9 bảng + 4 views + trigger
    └── 02_import_data.sql    # Dữ liệu lịch sử 2025-T2/2026
```

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.13 |
| PDF parsing | pdfplumber |
| Database | PostgreSQL 14 (psycopg2-binary) |
| Email parsing | Python `email` module (stdlib) |
| Dashboard | *(Hạng mục B — đang phát triển)* |
| Forecasting | *(Hạng mục C — đang phát triển)* |

---

## Liên hệ

datasync5ueh@gmail.com
