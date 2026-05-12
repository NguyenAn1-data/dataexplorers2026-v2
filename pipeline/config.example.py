"""
config.example.py — Cấu hình cơ sở dữ liệu PostgreSQL
Copy file này → config.py và điền thông tin kết nối của bạn
"""

# ═══════════════════════════════════════════════════════════════════════════
# CẤU HÌNH DATABASE PostgreSQL
# ═══════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host":     "localhost",      # Địa chỉ PostgreSQL server
    "port":     5432,              # Port mặc định PostgreSQL
    "dbname":   "tnbike_db",       # Tên database
    "user":     "postgres",        # Username PostgreSQL
    "password": "123456",          # Password (thay bằng password của bạn)
    "options":  "-c search_path=tnbike,public",
}

# ═══════════════════════════════════════════════════════════════════════════
# ĐƯỜNG DẪN FILE ĐẦU VÀO
# ═══════════════════════════════════════════════════════════════════════════

# Thư mục chứa 1.132 file .eml (email từ KH đặt hàng T3/2026)
EML_FOLDER = r"D:\email_data\eml_files"

# Thư mục logs (tự tạo nếu chưa có)
LOG_FOLDER = "logs"

# ═══════════════════════════════════════════════════════════════════════════
# CẤU HÌNH PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

# Số lượng file EML cần xử lý (-1 = toàn bộ)
LIMIT_FILES = -1

# Enable verbose logging
DEBUG = True
