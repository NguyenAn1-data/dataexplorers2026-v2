"""
config.example.py
Sao chép file này thành config.py và điền thông tin kết nối database của bạn.
"""

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "tnbike_db",
    "user":     "postgres",
    "password": "YOUR_PASSWORD_HERE",
    "options":  "-c search_path=tnbike,public",
}

EML_FOLDER = r"C:\path\to\tnbike_emails_mar2026"
PDF_FOLDER = r"C:\path\to\tnbike_pdfs_mar2026"

LOG_FOLDER = r"C:\path\to\pipeline\logs"

# Tolerance kiểm tra line_total = qty * unit_price (VND)
AMOUNT_TOLERANCE = 50
