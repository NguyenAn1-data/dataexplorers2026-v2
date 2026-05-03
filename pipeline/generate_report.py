"""
generate_report.py
Tạo báo cáo kỹ thuật PDF (10-15 trang) cho Hạng mục A & D.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import date
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "Bao_cao_ky_thuat_DataSync.pdf")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Font chứa Unicode/tiếng Việt: dùng DejaVu (đi kèm fpdf2)
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Dùng font helvetica (latin) và encode bằng latin-1 mapping
        # fpdf2 hỗ trợ Unicode natively với core fonts ở chế độ UTF-8
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("DejaVu", "", "DejaVuSansCondensed.ttf", uni=True) if False else None

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "DATA EXPLORERS 2026 - Vong 2 | Nhom DataSync | Bao cao Ky thuat",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}", align="C")

    def title_page(self):
        self.add_page()
        self.ln(30)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(30, 90, 160)
        self.cell(0, 12, "BAO CAO KY THUAT", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, "DATA EXPLORERS 2026 - Vong 2", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "From Data to Decision by MEXC Ventures", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 90, 160)
        self.cell(0, 10, "NHOM DATASYNC", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        members = [
            "Nguyen Dang Hoang An (Nhom truong)",
            "Le Thien Duc",
            "Ta Ngoc Bao Ngan",
            "Nguyen Trang Nhat Mai",
            "Nguyen Quynh Tram",
        ]
        for m in members:
            self.cell(0, 8, m, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, f"Hoc vien Chinh sach va Phat trien", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 7, f"Email: datasync5ueh@gmail.com", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 7, f"Ngay hoan thanh: {date.today().strftime('%d/%m/%Y')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section_title(self, text, level=1):
        self.ln(5)
        if level == 1:
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(30, 90, 160)
            self.set_fill_color(230, 240, 255)
            self.cell(0, 9, text, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(50, 50, 150)
            self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def body(self, text, indent=0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet(self, text, indent=5):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.l_margin + indent
        self.set_x(x)
        self.cell(4, 6, chr(149))
        self.set_x(x + 5)
        self.multi_cell(0, 6, text)

    def kv(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        self.cell(55, 6, key + ":", new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, value)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            w = (self.w - self.l_margin - self.r_margin) / len(headers)
            col_widths = [w] * len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(30, 90, 160)
        self.set_text_color(255, 255, 255)
        for h, cw in zip(headers, col_widths):
            self.cell(cw, 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        for i, row in enumerate(rows):
            self.set_fill_color(245, 248, 255) if i % 2 == 0 else self.set_fill_color(255, 255, 255)
            for cell, cw in zip(row, col_widths):
                self.cell(cw, 6, str(cell), border=1, fill=True)
            self.ln()
        self.ln(3)

    def code_block(self, code_text):
        self.set_font("Courier", "", 8)
        self.set_fill_color(245, 245, 245)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, code_text, fill=True, border=1)
        self.ln(2)


def build_report():
    pdf = PDF()

    # ── Trang bìa ──────────────────────────────────────────────────────────
    pdf.title_page()

    # ── Trang 2: Mục lục ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("MUC LUC")
    toc = [
        ("1.", "Tong quan du an va boi canh", "3"),
        ("2.", "Hang muc A: Xu ly don hang tu dong", "4"),
        ("2.1", "Kien truc pipeline", "4"),
        ("2.2", "Thu vien va cong nghe", "5"),
        ("2.3", "Xu ly file .eml (parse_eml.py)", "5"),
        ("2.4", "Trich xuat PDF (parse_pdf.py)", "6"),
        ("2.5", "Kiem tra hop le (validate.py)", "7"),
        ("2.6", "Ghi database (db_writer.py)", "8"),
        ("2.7", "Dieu phoi pipeline (main.py)", "9"),
        ("2.8", "Xu ly truong hop dac biet", "9"),
        ("3.", "Ket qua dat duoc", "10"),
        ("4.", "Schema database", "11"),
        ("5.", "Huong dan cai dat va chay", "12"),
        ("6.", "Ket luan va ke hoach tiep theo", "13"),
    ]
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    for num, title, page in toc:
        pdf.cell(12, 7, num)
        pdf.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # ── Trang 3: Tổng quan ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("1. TONG QUAN DU AN VA BOI CANH")
    pdf.body(
        "Cong ty Co phan Xe dap Thong Nhat la doanh nghiep san xuat/phan phoi xe dap voi quy mo "
        "hon 200 SKU, 5 nhom san pham chinh, van hanh theo mo hinh B2B voi hon 700 dai ly tren "
        "ca nuoc. Hien tai, dai ly dat hang qua email/dien thoai/Zalo, nhan vien nhap thu cong "
        "vao he thong ERP - quy trinh ton thoi gian va de sai sot."
    )
    pdf.ln(3)
    pdf.body("Muc tieu Vong 2 - DATA EXPLORERS 2026:")
    items = [
        "Tu dong hoa xu ly 1.132 don hang email thang 3/2026",
        "Xay dung dashboard phan tich kinh doanh da chieu (2025 - T3/2026)",
        "Du bao nhu cau Q2/2026 theo san pham, mau sac, hoat dong dai ly",
        "Trinh bay va bao ve truoc Hoi dong giam khao",
    ]
    for it in items:
        pdf.bullet(it)
    pdf.ln(4)
    pdf.section_title("Phan bo diem", level=2)
    pdf.table(
        ["Hang muc", "Noi dung", "Diem toi da"],
        [
            ["A", "Van hanh: Xu ly don hang tu dong", "25"],
            ["B", "Phan tich: Dashboard & Insights", "30"],
            ["C", "Du bao nhu cau & Chien luoc", "30"],
            ["D", "Trinh bay & Bao ve", "15"],
            ["Tong", "", "100"],
        ],
        [30, 110, 30]
    )

    # ── Trang 4-5: Hạng mục A ─────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("2. HANG MUC A: XU LY DON HANG TU DONG (25 DIEM)")
    pdf.body(
        "Nhom chon Phuong an A (Email + PDF .eml) de dat muc toi da 25/25 diem. Pipeline duoc "
        "viet bang Python, chay hoan toan tu dong khong can can thiep thu cong sau khi khoi dong."
    )

    pdf.section_title("2.1 Kien truc Pipeline", level=2)
    pdf.code_block(
        "1.132 file .eml\n"
        "      |\n"
        "      v\n"
        " parse_eml.py   <- Phan tich email: From, Subject, Date, Message-ID, PDF MIME attachment\n"
        "      |\n"
        "      v\n"
        " parse_pdf.py   <- Trich xuat PDF: so don, ngay, MST, ten KH, bang san pham\n"
        "      |\n"
        "      v\n"
        " validate.py    <- Kiem tra hop le: trung lap, ngay, ma hang, so luong, thanh tien\n"
        "      |\n"
        "      v\n"
        " db_writer.py   <- Ghi vao PostgreSQL: email_log -> sales_order -> order_line -> fact_sales"
    )
    pdf.body(
        "Pipeline thiet ke theo nguyen tac idempotent: co the chay lai nhieu lan ma khong gay "
        "trung lap du lieu. Co che: kiem tra message_id (chi tiep tuc neu chua co trong email_log "
        "voi status=SUCCESS) va so_number (kiem tra trong sales_order truoc khi insert)."
    )

    pdf.section_title("2.2 Thu vien va Cong nghe", level=2)
    pdf.table(
        ["Thu vien", "Phien ban", "Muc dich"],
        [
            ["Python", "3.13", "Ngon ngu lap trinh chinh"],
            ["pdfplumber", ">=0.10.0", "Trich xuat bang bieu tu PDF"],
            ["psycopg2-binary", ">=2.9.0", "Ket noi PostgreSQL"],
            ["email (stdlib)", "built-in", "Phan tich cau truc MIME cua .eml"],
        ],
        [40, 30, 100]
    )

    pdf.add_page()
    pdf.section_title("2.3 Xu ly file .eml - parse_eml.py", level=2)
    pdf.body(
        "Moi email co cau truc MIME phuc tap: header co the ma hoa Base64 hoac Quoted-Printable, "
        "file PDF dinh kem la payload nhi phan. Ham parse_eml() xu ly:"
    )
    items = [
        "Giai ma header: su dung decode_header() xu ly ca UTF-8 va ASCII",
        "Trich message_id, from_address, received_at (parsedate_to_datetime)",
        "Trich so don hang tu Subject bang regex: r\"BH26[._](\\d+)\"",
        "Tim PDF dinh kem trong cay MIME (Content-Type: application/pdf)",
        "Giai ma base64 lay pdf_bytes tra ve",
        "Trich MST tu email body bang regex: r\"MST[:\\s]*([0-9]{9,10})\"",
    ]
    for it in items:
        pdf.bullet(it)

    pdf.section_title("2.4 Trich xuat PDF - parse_pdf.py", level=2)
    pdf.body(
        "Su dung pdfplumber de trich xuat bang bieu tu PDF. Moi don hang co the trai dai "
        "nhieu trang (3-5 trang voi don hang lon). Cach xu ly:"
    )
    items = [
        "Trang dau, bang dau = bang header: so don, ngay, MST, ten dai ly",
        "Cac bang con lai (moi trang) = bang san pham: STT | Ma hang | Ten SP | DVT | SL | Don gia | Thanh tien",
        "Loc dong tieu de (STT header row) va dong tong cong (Tong cong row)",
        "Ham _is_product_code() nhan dien ma hang: so thuan 10-16 ky tu HOAC dang TP0099.0000570",
        "Ham _parse_amount() xu ly so VND: '1.898.148' -> 1898148.0 (cham la phan ngan)",
    ]
    for it in items:
        pdf.bullet(it)
    pdf.body(
        "Kho khan: PDF tao tu phien ban tieng Viet nen ten san pham bi garble unicode, "
        "tuy nhien cac truong du lieu quan trong (ma hang, so luong, don gia) la ASCII nen "
        "khong bi anh huong."
    )

    pdf.add_page()
    pdf.section_title("2.5 Kiem tra hop le - validate.py", level=2)
    pdf.body("Pipeline kiem tra 5 nhom dieu kien truoc khi ghi database:")
    pdf.table(
        ["Nhom kiem tra", "Noi dung", "Xu ly khi loi"],
        [
            ["1. So don hang", "Phai co so_number, khong duoc trung voi DB", "Fatal - bo qua don"],
            ["2. Ngay dat hang", "Phai thuoc thang 3/2026", "Ghi loi, bo qua"],
            ["3. Khach hang", "Phai co MST trong PDF hoac email body", "Ghi loi"],
            ["4. Ma san pham", "Phai ton tai trong bang product cua DB", "Ghi loi tong hop"],
            ["5. So luong & gia", "qty > 0, gia >= 0, thanh tien khop", "Ghi loi tung dong"],
        ],
        [35, 95, 42]
    )
    pdf.body(
        "Kiem tra thanh tien dung dual-tolerance de xu ly ca don hang so luong lon (>100 chiec) "
        "va don gia le thap phan:"
    )
    pdf.code_block(
        "expected = qty * unit_price\n"
        "abs_diff = abs(expected - line_total)\n"
        "rel_diff = abs_diff / line_total  # relative tolerance\n"
        "# Chi bao loi neu CA HAI vuot nguong:\n"
        "if abs_diff > 50 and rel_diff > 0.0001:  # 50 VND tuyet doi VA 0.01% tuong doi\n"
        "    errors.append(...)"
    )

    pdf.section_title("2.6 Ghi database - db_writer.py", level=2)
    pdf.body("Toan bo viec ghi du lieu trong 1 transaction de dam bao tinh nhat quan:")
    items = [
        "Lookup customer_code tu tax_code (MST): khop chinh xac, roi khop sau khi LTRIM('0')",
        "INSERT email_log: ghi trang thai ngay tu dau (PROCESSING)",
        "INSERT sales_order: so don, ngay, khach hang, tong tien/sl (trigger tu dong cap nhat)",
        "INSERT order_line (execute_batch): chèn nhanh toan bo dong san pham 1 lan",
        "UPDATE email_log: doi status -> SUCCESS/ERROR",
        "populate_fact_sales(): INSERT...SELECT ket noi 7 bang, NOT EXISTS de tranh trung",
    ]
    for it in items:
        pdf.bullet(it)

    pdf.add_page()
    pdf.section_title("2.7 Dieu phoi Pipeline - main.py", level=2)
    pdf.body(
        "main.py ket noi cac module lai, xu ly toan bo 1.132 file voi progress bar, "
        "ghi log chi tiet va xuat summary.json sau khi chay xong:"
    )
    pdf.code_block(
        "for eml_path in eml_files:\n"
        "    eml = parse_eml(eml_path)          # B1: parse email\n"
        "    pdf = parse_pdf(eml['pdf_bytes'])   # B2: parse PDF\n"
        "    errs = validate_order(eml, pdf, valid_products, existing_so)\n"
        "    if errs: log_error(); continue      # B3: validate\n"
        "    customer = lookup_customer(conn, mst)\n"
        "    insert_order(conn, eml, pdf, customer)  # B4-5: ghi DB\n"
        "    existing_so.add(so_number)          # cap nhat cache"
    )

    pdf.section_title("2.8 Xu ly Truong hop Dac biet", level=2)
    pdf.body("Trong qua trinh chay, phat hien va xu ly cac van de phat sinh:")
    pdf.table(
        ["Van de", "So luong", "Giai phap"],
        [
            ["KH moi (MST chua co trong DB)", "92 MST", "fix_missing_data.py: tu dong them KH moi"],
            ["Ma san pham moi chua co trong DB", "~30 ma", "fix_all_remaining.py: tu dong them SP moi"],
            ["Ma SP dang TP0099.0000570 (co dau cham)", "2 don", "Cap nhat _is_product_code() regex"],
            ["Sai lech thanh tien > 50 VND (don lon)", "1 don", "Them relative tolerance 0.01%"],
            ["Email trung (da xu ly o lan chay truoc)", "Nhieu", "Skip qua message_id cache"],
        ],
        [65, 25, 82]
    )

    # ── Trang 10: Kết quả ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("3. KET QUA DAT DUOC")
    pdf.body("Sau khi chay pipeline va xu ly cac truong hop dac biet:")
    pdf.table(
        ["Bang", "So hang", "Mo ta"],
        [
            ["email_log", "1.132 rows (100% SUCCESS)", "Trang thai xu ly tung email"],
            ["sales_order", "1.132 rows", "Don hang BH26.0935 -> BH26.2066"],
            ["order_line", "8.721 rows", "Chi tiet san pham tung don hang"],
            ["fact_sales (T3/2026)", "8.721 rows", "Du lieu phan tich doanh thu"],
        ],
        [40, 58, 74]
    )
    pdf.body("Thong ke doanh thu thang 3/2026:")
    pdf.table(
        ["Chi so", "Gia tri"],
        [
            ["Tong don hang", "1.132 don"],
            ["Tong so luong", "25.489 chiec"],
            ["Tong doanh thu", "~40,7 ty VND (40.691.947.133 VND)"],
            ["Doanh thu binh quan/don", "~35,9 trieu VND"],
            ["So dong san pham trung binh/don", "7,7 dong"],
        ],
        [70, 100]
    )
    pdf.body(
        "100% don hang thang 3/2026 da duoc xu ly thanh cong va ghi vao database, "
        "san sang cho cac buoc phan tich o Hang muc B va C."
    )

    # ── Trang 11: Schema ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("4. SCHEMA DATABASE")
    pdf.body(
        "Database: tnbike_db | Schema: tnbike | PostgreSQL 14\n"
        "Gom 9 bang chinh + 4 views + 1 trigger tu dong cap nhat tong tien:"
    )
    pdf.table(
        ["Bang", "So hang (sau pipeline)", "Mo ta"],
        [
            ["product_group", "5", "Nhom san pham (Tre Em, Dia Hinh,...)"],
            ["product_line", "~75", "Dong san pham"],
            ["product", "247+", "SKU san pham (ma hang, ten, don vi)"],
            ["product_price", "247+", "Lich su gia ban"],
            ["province", "63", "Tinh/thanh pho + vung mien"],
            ["customer", "700+", "Dai ly (ma KH, ten, MST, tinh, tier)"],
            ["sales_order", "1.132 T3/2026", "Don hang (so, ngay, KH, tong)"],
            ["order_line", "8.721 T3/2026", "Dong san pham (ma, SL, gia, thanh tien)"],
            ["fact_sales", "8.721 T3/2026", "Bang phan tich (full dimension)"],
            ["email_log", "1.132", "Nhat ky xu ly email (them boi pipeline)"],
        ],
        [38, 50, 84]
    )
    pdf.body(
        "Trigger trg_order_line_after_insert: sau moi INSERT vao order_line, "
        "tu dong cap nhat total_amount, total_quantity, line_count trong sales_order."
    )

    # ── Trang 12: Cài đặt ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("5. HUONG DAN CAI DAT VA CHAY")
    pdf.section_title("Yeu cau he thong", level=2)
    items = [
        "Python 3.11+ (khuyen nghi 3.13)",
        "PostgreSQL 14+ (port 5432)",
        "RAM toi thieu 4GB",
        "OS: Windows 10/11 hoac Linux/macOS",
    ]
    for it in items:
        pdf.bullet(it)
    pdf.section_title("Cac buoc cai dat", level=2)
    steps = [
        ("B1: Clone repo", "git clone https://github.com/NguyenAn1-data/dataexplorers2026-v2.git\ncd dataexplorers2026-v2"),
        ("B2: Cai thu vien", "pip install -r pipeline/requirements.txt"),
        ("B3: Cau hinh DB", "copy pipeline\\config.example.py pipeline\\config.py\n# Sua config.py: dien mat khau PostgreSQL va duong dan thu muc email"),
        ("B4: Khoi tao DB", "cd pipeline\npython setup_db.py\n# -> Tao tnbike_db, chay 01_create_tables.sql + 02_import_data.sql"),
        ("B5: Chay pipeline", "python main.py\n# -> Xu ly 1.132 file .eml, ghi vao database\n# -> Xem ket qua: logs/summary.json"),
    ]
    for title, code in steps:
        pdf.body(title)
        pdf.code_block(code)

    pdf.section_title("Kiem tra ket qua", level=2)
    pdf.body("Sau khi chay pipeline, kiem tra trong pgAdmin hoac psql:")
    pdf.code_block(
        "-- Kiem tra email_log\nSELECT processing_status, COUNT(*) FROM tnbike.email_log GROUP BY 1;\n\n"
        "-- Kiem tra doanh thu T3/2026\nSELECT COUNT(*), SUM(total_amount) FROM tnbike.sales_order\n"
        "WHERE fiscal_year=2026 AND fiscal_month=3;\n\n"
        "-- Ket qua mong doi: 1132 SUCCESS, tong ~40.7 ty VND"
    )

    # ── Trang 13-14: Kết luận ─────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("6. KET LUAN VA KE HOACH TIEP THEO")
    pdf.section_title("Ket qua Hang muc A", level=2)
    pdf.body(
        "Nhom da xay dung thanh cong pipeline xu ly don hang tu dong dat 100% hieu qua "
        "(1.132/1.132 don hang). Phuong an A (Email + PDF) duoc chon de toi da hoa diem so. "
        "Pipeline co kha nang:"
    )
    items = [
        "Xu ly cau truc MIME phuc tap cua email (base64, quoted-printable, multi-part)",
        "Trich xuat chinh xac du lieu tu PDF nhieu trang bang pdfplumber",
        "Kiem tra hop le toan dien voi dual-tolerance cho tinh toan tai chinh",
        "Tu dong dang ky khach hang va san pham moi phat hien trong email",
        "Chay idempotent: an toan khi restart, khong gay du lieu trung lap",
        "Ghi du lieu theo dung schema: email_log, sales_order, order_line, fact_sales",
    ]
    for it in items:
        pdf.bullet(it)

    pdf.section_title("Ke hoach tiep theo", level=2)
    pdf.table(
        ["Hang muc", "Noi dung", "Trang thai"],
        [
            ["B - Dashboard", "6 man hinh Power BI/Metabase, BCG matrix, RFM", "Dang thuc hien"],
            ["C - Du bao", "Prophet/SARIMA du bao Q2/2026, LLM integration", "Chua bat dau"],
            ["D - Bao cao", "Bao cao ky thuat, Slide 10-15 trang, Video 5-7 phut", "Dang thuc hien"],
        ],
        [30, 110, 32]
    )

    pdf.body(
        "Du lieu T3/2026 da san sang trong database, cung voi lich su 2025-T2/2026, "
        "tao nen nen tang du lieu day du cho phan tich va du bao o cac hang muc tiep theo."
    )

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "---", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, "Bao cao nay duoc tao tu dong boi generate_report.py", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Nhom DataSync | DATA EXPLORERS 2026 | {date.today().strftime('%d/%m/%Y')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(OUTPUT_PATH)
    print(f"Da tao bao cao: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_report()
    print(f"Mo file: {os.path.abspath(path)}")
