# ⚡ QUICK START — 5 bước chạy Pipeline

**Cho những người muốn chạy nhanh (giả sử đã có Python + PostgreSQL)**

---

## 1️⃣ Cài thư viện
```powershell
cd "d:\Data explore vòng 2\pipeline"
pip install -r requirements.txt
```

---

## 2️⃣ Tạo config
```powershell
copy config.example.py config.py
```

Mở `config.py`, sửa:
- `password`: Password PostgreSQL của bạn
- `EML_FOLDER`: Đường dẫn thư mục chứa file .eml

---

## 3️⃣ Khởi tạo DB
```powershell
python setup_db.py
```

---

## 4️⃣ Chạy Pipeline
```powershell
python main.py
```

**Chờ khoảng 5-10 phút**

---

## 5️⃣ Kiểm tra kết quả
Tìm dòng:
```
SUCCESS:         1132 đơn hàng
LINES:           8721 dòng sản phẩm
```

✅ **Hoàn thành!**

---

## ❌ Lỗi?
→ Xem [PHASE_A_INSTALLATION_GUIDE.md](../PHASE_A_INSTALLATION_GUIDE.md#-xử-lý-lỗi)
