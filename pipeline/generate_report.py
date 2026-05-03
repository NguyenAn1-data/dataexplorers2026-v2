"""
generate_report.py
Tạo báo cáo kỹ thuật PDF tiếng Việt cho Hạng mục A & D.
Dùng font Arial TTF để hỗ trợ đầy đủ ký tự tiếng Việt.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import date
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "Bao_cao_ky_thuat_DataSync.pdf")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

ARIAL        = "C:\\Windows\\Fonts\\arial.ttf"
ARIAL_BOLD   = "C:\\Windows\\Fonts\\arialbd.ttf"
ARIAL_ITALIC = "C:\\Windows\\Fonts\\ariali.ttf"
ARIAL_BI     = "C:\\Windows\\Fonts\\arialbi.ttf"
MONO         = "C:\\Windows\\Fonts\\CascadiaMono.ttf"


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("Arial", "",  ARIAL)
        self.add_font("Arial", "B", ARIAL_BOLD)
        self.add_font("Arial", "I", ARIAL_ITALIC)
        self.add_font("Arial", "BI", ARIAL_BI)
        self.add_font("Mono",  "",  MONO)

    def header(self):
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 7, "DATA EXPLORERS 2026 – Vòng 2  |  Nhóm DataSync  |  Báo cáo Kỹ thuật",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Trang {self.page_no()}", align="C")

    def title_page(self):
        self.add_page()
        self.ln(25)
        self.set_font("Arial", "B", 24)
        self.set_text_color(20, 80, 160)
        self.cell(0, 13, "BÁO CÁO KỸ THUẬT", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Arial", "B", 16)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, "DATA EXPLORERS 2026 – Vòng 2", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Arial", "I", 12)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, "From Data to Decision by MEXC Ventures", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(18)

        # Khung thông tin nhóm
        self.set_fill_color(235, 243, 255)
        self.set_draw_color(20, 80, 160)
        box_x = self.l_margin + 20
        box_w = self.w - 2 * self.l_margin - 40
        self.set_x(box_x)
        self.cell(box_w, 10, "", border="TLR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(box_x)
        self.set_font("Arial", "B", 15)
        self.set_text_color(20, 80, 160)
        self.cell(box_w, 11, "NHÓM DATASYNC", align="C", border="LR", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Arial", "", 11)
        self.set_text_color(30, 30, 30)
        members = [
            ("Nguyễn Đăng Hoàng Ân", "Nhóm trưởng"),
            ("Lê Thiên Đức", "Thành viên"),
            ("Tạ Ngọc Bảo Ngân", "Thành viên"),
            ("Nguyễn Trang Nhật Mai", "Thành viên"),
            ("Nguyễn Quỳnh Trâm", "Thành viên"),
        ]
        for name, role in members:
            self.set_x(box_x)
            self.cell(box_w // 2 + 5, 9, f"  {name}", border="L", fill=True)
            self.cell(box_w - box_w // 2 - 5, 9, role, border="R", fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(box_x)
        self.cell(box_w, 10, "", border="BLR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(18)
        self.set_font("Arial", "", 10)
        self.set_text_color(110, 110, 110)
        self.cell(0, 7, f"Email liên hệ: datasync5ueh@gmail.com", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 7, f"Ngày hoàn thành: {date.today().strftime('%d/%m/%Y')}", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def h1(self, text):
        self.ln(5)
        self.set_font("Arial", "B", 13)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(20, 80, 160)
        self.cell(0, 9, f"  {text}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def h2(self, text):
        self.ln(3)
        self.set_font("Arial", "B", 11)
        self.set_text_color(20, 80, 160)
        self.set_fill_color(235, 243, 255)
        self.cell(0, 8, f"  {text}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def para(self, text, indent=0):
        self.set_font("Arial", "", 10)
        self.set_text_color(25, 25, 25)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet(self, text, indent=6):
        self.set_font("Arial", "", 10)
        self.set_text_color(25, 25, 25)
        x = self.l_margin + indent
        self.set_x(x)
        self.cell(5, 6, "•")
        self.set_x(x + 5)
        self.multi_cell(0, 6, text)

    def table(self, headers, rows, col_widths=None, header_bg=(20, 80, 160)):
        avail = self.w - self.l_margin - self.r_margin
        if col_widths is None:
            w = avail / len(headers)
            col_widths = [w] * len(headers)
        # Header
        self.set_font("Arial", "B", 9)
        self.set_fill_color(*header_bg)
        self.set_text_color(255, 255, 255)
        for h, cw in zip(headers, col_widths):
            self.cell(cw, 7, h, border=1, fill=True, align="C")
        self.ln()
        # Rows
        self.set_font("Arial", "", 9)
        self.set_text_color(25, 25, 25)
        for i, row in enumerate(rows):
            if i % 2 == 0:
                self.set_fill_color(244, 248, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for cell_txt, cw in zip(row, col_widths):
                self.cell(cw, 6, str(cell_txt), border=1, fill=True)
            self.ln()
        self.ln(3)

    def code(self, text):
        self.set_font("Mono", "", 8)
        self.set_fill_color(246, 246, 246)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.8, text, fill=True, border=1)
        self.ln(2)


# ---------------------------------------------------------------------------
def build_report():
    pdf = PDF()

    # ── TRANG BÌA ────────────────────────────────────────────────────────────
    pdf.title_page()

    # ── MỤC LỤC ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("MỤC LỤC")
    toc = [
        ("1.",   "Tổng quan dự án và bối cảnh",                     "3"),
        ("2.",   "Hạng mục A: Xử lý đơn hàng tự động",             "4"),
        ("2.1",  "Kiến trúc pipeline",                               "4"),
        ("2.2",  "Thư viện và công nghệ sử dụng",                   "4"),
        ("2.3",  "Xử lý file .eml – parse_eml.py",                  "5"),
        ("2.4",  "Trích xuất PDF – parse_pdf.py",                   "6"),
        ("2.5",  "Kiểm tra hợp lệ – validate.py",                   "7"),
        ("2.6",  "Ghi database – db_writer.py",                     "8"),
        ("2.7",  "Điều phối pipeline – main.py",                    "9"),
        ("2.8",  "Xử lý trường hợp đặc biệt",                      "9"),
        ("3.",   "Kết quả đạt được",                                "10"),
        ("4.",   "Schema database",                                 "11"),
        ("5.",   "Hướng dẫn cài đặt và chạy",                      "12"),
        ("6.",   "Kết luận và kế hoạch tiếp theo",                 "13"),
    ]
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(25, 25, 25)
    for num, title, pg in toc:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(14, 7, num)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # ── TỔNG QUAN ────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("1. TỔNG QUAN DỰ ÁN VÀ BỐI CẢNH")
    pdf.para(
        "Công ty Cổ phần Xe đạp Thống Nhất là doanh nghiệp sản xuất và phân phối xe đạp với hơn "
        "200 SKU, 5 nhóm sản phẩm chính, vận hành theo mô hình B2B với hơn 700 đại lý trên toàn "
        "quốc. Hiện tại, đại lý đặt hàng qua email, điện thoại hoặc Zalo; nhân viên phải nhập "
        "thủ công vào hệ thống ERP, dẫn đến tốn nhiều thời gian và dễ xảy ra sai sót."
    )
    pdf.para("Mục tiêu Vòng 2 – DATA EXPLORERS 2026:")
    for item in [
        "Tự động hóa xử lý 1.132 đơn hàng email tháng 3/2026.",
        "Xây dựng dashboard phân tích kinh doanh đa chiều (dữ liệu 2025 – T3/2026).",
        "Dự báo nhu cầu Q2/2026 theo sản phẩm, màu sắc và hoạt động đại lý.",
        "Trình bày và bảo vệ kết quả trước hội đồng giám khảo.",
    ]:
        pdf.bullet(item)
    pdf.ln(3)
    pdf.h2("Phân bổ điểm")
    pdf.table(
        ["Hạng mục", "Nội dung", "Điểm"],
        [
            ["A", "Vận hành: Xử lý đơn hàng tự động", "25"],
            ["B", "Phân tích: Dashboard & Insights", "30"],
            ["C", "Dự báo nhu cầu & Chiến lược", "30"],
            ["D", "Trình bày & Bảo vệ", "15"],
            ["Tổng", "", "100"],
        ],
        [20, 130, 20]
    )

    # ── HẠNG MỤC A ───────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("2. HẠNG MỤC A: XỬ LÝ ĐƠN HÀNG TỰ ĐỘNG (25 ĐIỂM)")
    pdf.para(
        "Nhóm chọn Phương án A (Email + PDF, file .eml) để đạt mức tối đa 25/25 điểm. "
        "Pipeline được viết hoàn toàn bằng Python, tự động xử lý từ đầu đến cuối mà không cần "
        "can thiệp thủ công sau khi khởi động."
    )

    pdf.h2("2.1  Kiến trúc Pipeline")
    pdf.code(
        "1.132 file .eml\n"
        "      |\n"
        "      v\n"
        " parse_eml.py   <-- Phân tích email: From, Subject, Date, Message-ID, file PDF đính kèm\n"
        "      |\n"
        "      v\n"
        " parse_pdf.py   <-- Trích xuất PDF: số đơn, ngày, MST, tên khách hàng, bảng sản phẩm\n"
        "      |\n"
        "      v\n"
        " validate.py    <-- Kiểm tra hợp lệ: trùng lặp, ngày tháng, mã hàng, số lượng, thành tiền\n"
        "      |\n"
        "      v\n"
        " db_writer.py   <-- Ghi vào PostgreSQL: email_log -> sales_order -> order_line -> fact_sales"
    )
    pdf.para(
        "Pipeline thiết kế theo nguyên tắc idempotent: có thể chạy lại nhiều lần mà không gây "
        "trùng lặp dữ liệu. Cơ chế: kiểm tra message_id (chỉ xử lý nếu chưa có trong email_log "
        "với trạng thái SUCCESS) và so_number (kiểm tra trong sales_order trước khi INSERT)."
    )

    pdf.h2("2.2  Thư viện và Công nghệ sử dụng")
    pdf.table(
        ["Thư viện / Công nghệ", "Phiên bản", "Mục đích"],
        [
            ["Python", "3.13", "Ngôn ngữ lập trình chính"],
            ["pdfplumber", ">=0.10.0", "Trích xuất bảng biểu từ PDF"],
            ["psycopg2-binary", ">=2.9.0", "Kết nối và ghi dữ liệu vào PostgreSQL"],
            ["email (stdlib)", "built-in", "Phân tích cấu trúc MIME của file .eml"],
            ["PostgreSQL", "14+", "Cơ sở dữ liệu quan hệ lưu trữ đơn hàng"],
        ],
        [55, 30, 85]
    )

    # ── PARSE EML ────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("2. HẠNG MỤC A (tiếp theo)")
    pdf.h2("2.3  Xử lý file .eml – parse_eml.py")
    pdf.para(
        "Mỗi file .eml có cấu trúc MIME nhiều tầng: header có thể mã hóa Base64 hoặc "
        "Quoted-Printable, file PDF đính kèm là payload nhị phân. Hàm parse_eml() xử lý:"
    )
    for item in [
        "Giải mã header: dùng decode_header() để xử lý cả UTF-8 và ASCII.",
        "Trích message_id, from_address, received_at (parsedate_to_datetime).",
        "Trích số đơn hàng từ Subject bằng regex: BH26[._](\\d+).",
        "Tìm file PDF đính kèm trong cây MIME (Content-Type: application/pdf).",
        "Giải mã base64 lấy pdf_bytes trả về để bước tiếp theo xử lý.",
        "Trích MST từ body email bằng regex: MST[:\\s]*([0-9]{9,10}).",
    ]:
        pdf.bullet(item)

    pdf.h2("2.4  Trích xuất PDF – parse_pdf.py")
    pdf.para(
        "Dùng pdfplumber để trích xuất bảng biểu từ PDF. Mỗi đơn hàng có thể trải dài nhiều "
        "trang (thường 2–5 trang với đơn hàng có nhiều sản phẩm). Cách xử lý:"
    )
    for item in [
        "Trang đầu, bảng đầu tiên = bảng header đơn hàng: số đơn, ngày đặt, MST, tên đại lý.",
        "Các bảng còn lại (tất cả trang) = bảng sản phẩm: STT | Mã hàng | Tên SP | ĐVT | SL | Đơn giá | Thành tiền.",
        "Lọc dòng tiêu đề bảng (dòng STT) và dòng tổng cộng (STT trống, không có mã hàng).",
        "Hàm _is_product_code() nhận diện mã hàng: số thuần 10–16 ký tự HOẶC dạng TP0099.0000570.",
        "Hàm _parse_amount() xử lý số VND: '1.898.148' → 1898148.0 (dấu chấm là phân ngàn).",
        "Xử lý trường hợp PDF có encoding tiếng Việt bị garble – các trường số liệu (mã hàng, giá) vẫn là ASCII.",
    ]:
        pdf.bullet(item)

    # ── VALIDATE ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h2("2.5  Kiểm tra hợp lệ – validate.py")
    pdf.para("Pipeline kiểm tra 5 nhóm điều kiện trước khi ghi dữ liệu vào database:")
    pdf.table(
        ["Nhóm kiểm tra", "Nội dung", "Xử lý khi lỗi"],
        [
            ["1. Số đơn hàng", "Phải có so_number, không được trùng với DB", "Fatal – bỏ qua đơn"],
            ["2. Ngày đặt hàng", "Phải thuộc tháng 3/2026", "Ghi lỗi, bỏ qua"],
            ["3. Khách hàng", "Phải có MST trong PDF hoặc email body", "Ghi lỗi"],
            ["4. Mã sản phẩm", "Phải tồn tại trong bảng product của DB", "Ghi lỗi tổng hợp"],
            ["5. Số lượng & giá", "qty > 0, đơn giá >= 0, thành tiền khớp tính toán", "Ghi lỗi từng dòng"],
        ],
        [38, 100, 32]
    )
    pdf.para(
        "Kiểm tra thành tiền dùng dual-tolerance để xử lý cả đơn hàng số lượng lớn "
        "(đơn giá có phần lẻ thập phân) và đơn hàng thông thường:"
    )
    pdf.code(
        "expected  = qty * unit_price\n"
        "abs_diff  = abs(expected - line_total)\n"
        "rel_diff  = abs_diff / line_total        # sai lệch tương đối\n"
        "\n"
        "# Chỉ báo lỗi khi CẢ HAI điều kiện vượt ngưỡng:\n"
        "if abs_diff > 50 and rel_diff > 0.0001:  # 50 VND tuyệt đối VÀ 0,01% tương đối\n"
        "    errors.append(...)"
    )

    pdf.h2("2.6  Ghi database – db_writer.py")
    pdf.para("Toàn bộ việc ghi dữ liệu thực hiện trong một transaction để đảm bảo tính nhất quán:")
    for item in [
        "Tra cứu customer_code từ tax_code (MST): khớp chính xác, rồi khớp sau khi LTRIM('0').",
        "INSERT email_log: ghi trạng thái ngay từ đầu (PROCESSING).",
        "INSERT sales_order: số đơn, ngày, khách hàng – trigger tự động cập nhật tổng tiền/số lượng.",
        "INSERT order_line (execute_batch): chèn nhanh toàn bộ dòng sản phẩm trong một lần gọi.",
        "UPDATE email_log: đổi trạng thái thành SUCCESS hoặc ERROR kèm chi tiết lỗi.",
        "populate_fact_sales(): INSERT…SELECT kết nối 7 bảng, dùng NOT EXISTS để tránh trùng.",
    ]:
        pdf.bullet(item)

    # ── MAIN & ĐẶC BIỆT ──────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h2("2.7  Điều phối Pipeline – main.py")
    pdf.para(
        "main.py kết nối các module lại với nhau, hiển thị thanh tiến trình, ghi log chi tiết "
        "và xuất file summary.json sau khi chạy xong:"
    )
    pdf.code(
        "for eml_path in eml_files:\n"
        "    eml  = parse_eml(eml_path)              # Bước 1: phân tích email\n"
        "    pdf  = parse_pdf(eml['pdf_bytes'])       # Bước 2: trích xuất PDF\n"
        "    errs = validate_order(eml, pdf, ...)     # Bước 3: kiểm tra hợp lệ\n"
        "    if errs:\n"
        "        log_error(errs); continue\n"
        "    customer = lookup_customer(conn, mst)    # Bước 4: tra cứu khách hàng\n"
        "    insert_order(conn, eml, pdf, customer)   # Bước 5: ghi database\n"
        "    existing_so.add(so_number)               # Cập nhật cache tránh trùng"
    )

    pdf.h2("2.8  Xử lý Trường hợp Đặc biệt")
    pdf.para("Trong quá trình chạy, phát hiện và xử lý các vấn đề phát sinh sau:")
    pdf.table(
        ["Vấn đề", "Số lượng", "Giải pháp"],
        [
            ["Khách hàng mới (MST chưa có trong DB)", "92 MST", "fix_missing_data.py: tự động đăng ký KH mới"],
            ["Mã sản phẩm mới chưa có trong DB", "~30 mã", "fix_all_remaining.py: tự động thêm sản phẩm mới"],
            ["Mã SP dạng TP0099.0000570 (có dấu chấm)", "2 đơn", "Cập nhật regex _is_product_code()"],
            ["Sai lệch thành tiền > 50 VND (đơn lớn)", "1 đơn", "Thêm kiểm tra sai lệch tương đối 0,01%"],
            ["Email trùng (đã xử lý lần trước)", "Nhiều", "Bỏ qua qua cache message_id (chỉ SUCCESS)"],
        ],
        [68, 25, 77]
    )

    # ── KẾT QUẢ ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("3. KẾT QUẢ ĐẠT ĐƯỢC")
    pdf.para("Sau khi chạy pipeline và xử lý các trường hợp đặc biệt, toàn bộ 1.132 đơn hàng đã được ghi thành công:")
    pdf.table(
        ["Bảng", "Số dòng T3/2026", "Mô tả"],
        [
            ["email_log", "1.132 (100% SUCCESS)", "Nhật ký trạng thái xử lý từng email"],
            ["sales_order", "1.132 đơn hàng", "Đơn hàng BH26.0935 đến BH26.2066"],
            ["order_line", "8.721 dòng", "Chi tiết sản phẩm trong từng đơn"],
            ["fact_sales", "8.721 dòng", "Dữ liệu phân tích doanh thu đa chiều"],
        ],
        [35, 55, 80]
    )
    pdf.h2("Thống kê doanh thu tháng 3/2026")
    pdf.table(
        ["Chỉ số", "Giá trị"],
        [
            ["Tổng số đơn hàng", "1.132 đơn"],
            ["Tổng số lượng xe", "25.489 chiếc"],
            ["Tổng doanh thu", "40.691.947.133 VND (~40,7 tỷ VND)"],
            ["Doanh thu bình quân mỗi đơn", "~35,9 triệu VND"],
            ["Số dòng sản phẩm trung bình mỗi đơn", "7,7 dòng"],
            ["Tỷ lệ xử lý thành công", "100% (1.132/1.132)"],
        ],
        [90, 80]
    )
    pdf.para(
        "Toàn bộ dữ liệu tháng 3/2026 đã sẵn sàng trong database, cùng với lịch sử "
        "2025–T2/2026 (17.031 dòng fact_sales), tạo nền tảng cho phân tích và dự báo "
        "ở các hạng mục tiếp theo."
    )

    # ── SCHEMA ───────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("4. SCHEMA DATABASE")
    pdf.para(
        "Cơ sở dữ liệu: tnbike_db  |  Schema: tnbike  |  PostgreSQL 14\n"
        "Gồm 9 bảng chính + 4 views + 1 trigger tự động cập nhật tổng tiền đơn hàng:"
    )
    pdf.table(
        ["Bảng", "Số dòng (sau pipeline)", "Mô tả"],
        [
            ["product_group", "5", "Nhóm sản phẩm (Trẻ Em, Địa Hình, Phổ Thông,...)"],
            ["product_line", "~75", "Dòng sản phẩm trong từng nhóm"],
            ["product", "247+", "SKU sản phẩm (mã hàng, tên, đơn vị tính)"],
            ["product_price", "247+", "Lịch sử giá bán theo thời gian"],
            ["province", "63", "Tỉnh/thành phố và vùng miền"],
            ["customer", "700+", "Đại lý (mã KH, tên, MST, tỉnh, tier)"],
            ["sales_order", "1.132 T3/2026", "Đơn hàng (số đơn, ngày, KH, tổng tiền)"],
            ["order_line", "8.721 T3/2026", "Dòng sản phẩm (mã, số lượng, đơn giá, thành tiền)"],
            ["fact_sales", "8.721 T3/2026", "Bảng phân tích đầy đủ chiều dữ liệu"],
            ["email_log", "1.132", "Nhật ký xử lý email (bảng thêm bởi pipeline)"],
        ],
        [38, 48, 84]
    )
    pdf.para(
        "Trigger trg_order_line_after_insert: sau mỗi INSERT vào order_line, "
        "tự động cập nhật total_amount, total_quantity và line_count trong sales_order."
    )

    # ── CÀI ĐẶT ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("5. HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY")
    pdf.h2("Yêu cầu hệ thống")
    for item in [
        "Python 3.11+ (khuyến nghị 3.13)",
        "PostgreSQL 14+ (port 5432)",
        "RAM tối thiểu 4 GB",
        "Thư mục chứa 1.132 file .eml của tháng 3/2026",
    ]:
        pdf.bullet(item)
    pdf.h2("Các bước cài đặt")
    steps = [
        ("Bước 1: Sao chép mã nguồn",
         "git clone https://github.com/NguyenAn1-data/dataexplorers2026-v2.git\n"
         "cd dataexplorers2026-v2"),
        ("Bước 2: Cài thư viện Python",
         "pip install -r pipeline/requirements.txt"),
        ("Bước 3: Cấu hình database",
         "copy pipeline\\config.example.py pipeline\\config.py\n"
         "# Mở config.py, điền mật khẩu PostgreSQL và đường dẫn thư mục email"),
        ("Bước 4: Khởi tạo database",
         "cd pipeline\n"
         "python setup_db.py\n"
         "# Tạo tnbike_db, chạy 01_create_tables.sql + 02_import_data.sql"),
        ("Bước 5: Chạy pipeline",
         "python main.py\n"
         "# Xử lý 1.132 file .eml, ghi vào database\n"
         "# Xem kết quả tổng hợp: logs/summary.json"),
    ]
    for title, code_txt in steps:
        pdf.para(title)
        pdf.code(code_txt)

    pdf.h2("Kiểm tra kết quả trong pgAdmin")
    pdf.code(
        "-- Kiểm tra trạng thái xử lý email\n"
        "SELECT processing_status, COUNT(*)\n"
        "FROM tnbike.email_log\n"
        "GROUP BY processing_status;\n"
        "-- Kết quả mong đợi: SUCCESS = 1132\n\n"
        "-- Kiểm tra doanh thu tháng 3/2026\n"
        "SELECT COUNT(*) AS so_don, SUM(total_amount) AS doanh_thu\n"
        "FROM tnbike.sales_order\n"
        "WHERE fiscal_year = 2026 AND fiscal_month = 3;\n"
        "-- Kết quả mong đợi: 1132 đơn, ~40,7 tỷ VND"
    )

    # ── KẾT LUẬN ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("6. KẾT LUẬN VÀ KẾ HOẠCH TIẾP THEO")
    pdf.h2("Kết quả Hạng mục A")
    pdf.para(
        "Nhóm DataSync đã xây dựng thành công pipeline xử lý đơn hàng tự động đạt 100% hiệu quả "
        "(1.132/1.132 đơn hàng). Lựa chọn Phương án A (Email + PDF) thay vì chỉ đọc PDF giúp "
        "tối đa hóa điểm số (25 điểm thay vì 20 điểm). Pipeline có khả năng:"
    )
    for item in [
        "Xử lý cấu trúc MIME phức tạp của email (base64, quoted-printable, đa tầng).",
        "Trích xuất chính xác dữ liệu từ PDF nhiều trang bằng pdfplumber.",
        "Kiểm tra hợp lệ toàn diện với dual-tolerance cho tính toán tài chính.",
        "Tự động đăng ký khách hàng và sản phẩm mới phát hiện trong email.",
        "Chạy idempotent: an toàn khi khởi động lại, không gây dữ liệu trùng lặp.",
        "Ghi dữ liệu đúng schema: email_log, sales_order, order_line, fact_sales.",
    ]:
        pdf.bullet(item)

    pdf.h2("Kế hoạch tiếp theo")
    pdf.table(
        ["Hạng mục", "Nội dung", "Trạng thái"],
        [
            ["B – Dashboard", "6 màn hình Power BI/Metabase, BCG matrix, phân tích RFM", "Đang thực hiện"],
            ["C – Dự báo", "Mô hình Prophet/SARIMA dự báo Q2/2026, tích hợp LLM", "Chưa bắt đầu"],
            ["D – Trình bày", "Slide 10–15 trang, video demo 5–7 phút", "Đang thực hiện"],
        ],
        [25, 120, 25]
    )
    pdf.para(
        "Với nền tảng dữ liệu đầy đủ từ 2025 đến T3/2026, nhóm tự tin có thể xây dựng "
        "dashboard phân tích và mô hình dự báo có giá trị kinh doanh thực tế cho "
        "Công ty Cổ phần Xe đạp Thống Nhất."
    )

    pdf.ln(8)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 6, "Báo cáo được tạo tự động bởi generate_report.py", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Nhóm DataSync – DATA EXPLORERS 2026 – {date.today().strftime('%d/%m/%Y')}",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_report()
    print(f"Đã tạo báo cáo: {os.path.abspath(path)}")
