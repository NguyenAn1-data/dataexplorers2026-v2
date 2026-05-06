"""
parse_pdf.py
Trích xuất dữ liệu đơn hàng từ file PDF đính kèm:
  - Header: so_number, order_date, tax_code (MST), customer_name
  - Lines : product_code, quantity, unit_price, line_total
Xử lý cả PDF 1 trang và nhiều trang.
"""

import io
import re
from datetime import date

import pdfplumber


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_amount(raw: str) -> float:
    """Chuyển '1.898.148' (định dạng VN) → 1898148.0."""
    if not raw:
        return 0.0
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_int(raw: str) -> int:
    if not raw:
        return 0
    # Loại bỏ ký tự rác do PDF encoding: "ng: 55" → lấy số cuối
    digits = re.findall(r"\d+", raw)
    return int(digits[-1]) if digits else 0


def _parse_date(raw: str) -> date | None:
    """Chuyển '01/03/2026' → date(2026, 3, 1)."""
    raw = raw.strip()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def _is_product_code(s: str) -> bool:
    """Kiểm tra chuỗi có phải mã hàng hợp lệ không (chỉ chứa chữ số, 10-16 ký tự)."""
    s = s.strip()
    # Chuẩn: thuần số 10-16 ký tự (VD: 000225002023000)
    if re.fullmatch(r"\d{10,16}", s):
        return True
    # Đặc biệt: có chấm hoặc chữ, độ dài 8-20 (VD: TP0099.0000570, 156.01.12.0003)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-]{7,19}", s):
        return True
    return False


def _is_header_row(row: list) -> bool:
    """Bỏ qua dòng tiêu đề bảng (STT, Mã hàng, ...)."""
    if not row:
        return False
    first = str(row[0]).strip().upper()
    return first in ("STT", "S.T.T", "TT")


def _is_total_row(row: list) -> bool:
    """Bỏ qua dòng tổng cộng (STT trống, không có mã hàng)."""
    if not row or len(row) < 2:
        return False
    stt = str(row[0]).strip()
    code = str(row[1]).strip()
    # STT trống hoặc không phải số → dòng tổng
    return (not stt or not re.fullmatch(r"\d+", stt)) and not _is_product_code(code)


# ---------------------------------------------------------------------------
# Header parsing (Table 0, page 1)
# ---------------------------------------------------------------------------

def _parse_header_table(table: list) -> dict:
    """
    Table 0 thường có dạng:
      Row 0: ['Số đơn hàng:', 'BH26.0935', 'Ngày:',   '01/03/2026']
      Row 1: ['Đại lý:',      'TÊN ĐẠI LÝ',  'MST:',    '167397253']
      Row 2: ['Địa chỉ:',     '...',          '',        '']
    Các nhãn bị garble do encoding → dùng vị trí cột thay vì text nhãn.
    """
    result = {
        "so_number":     "",
        "order_date":    None,
        "tax_code":      "",
        "customer_name": "",
    }

    if not table or len(table) < 2:
        return result

    row0 = table[0]
    row1 = table[1] if len(table) > 1 else []

    # Row 0, col 1 = so_number; col 3 = date
    if len(row0) >= 2:
        raw_so = str(row0[1]).strip()
        m = re.search(r"BH26[._](\d+)", raw_so, re.IGNORECASE)
        if m:
            result["so_number"] = f"BH26.{m.group(1)}"

    if len(row0) >= 4:
        result["order_date"] = _parse_date(str(row0[3]))

    # Row 1, col 1 = customer_name; col 3 = MST
    if len(row1) >= 2:
        result["customer_name"] = str(row1[1]).strip()
    if len(row1) >= 4:
        raw_mst = str(row1[3]).strip()
        digits_only = re.sub(r"\D", "", raw_mst)
        if len(digits_only) >= 9:
            result["tax_code"] = digits_only

    return result


# ---------------------------------------------------------------------------
# Product line parsing (Table 1+, all pages)
# ---------------------------------------------------------------------------

def _parse_product_table(table: list) -> list[dict]:
    """
    Mỗi dòng hợp lệ: [STT, Mã hàng, Tên SP, ĐVT, SL, Đơn giá, Thành tiền]
    index:             0    1         2       3    4   5         6
    """
    lines = []
    for row in table:
        if len(row) < 7:
            continue
        if _is_header_row(row) or _is_total_row(row):
            continue

        product_code = str(row[1]).strip()
        if not _is_product_code(product_code):
            continue

        qty = _parse_int(str(row[4]))
        unit_price = _parse_amount(str(row[5]))
        line_total = _parse_amount(str(row[6]))

        if qty <= 0 or unit_price < 0:
            continue

        lines.append({
            "product_code": product_code,
            "quantity":     qty,
            "unit_price":   unit_price,
            "line_total":   line_total,
        })

    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_pdf(pdf_bytes: bytes) -> dict:
    """
    Đọc PDF từ bytes, trả về:
      so_number, order_date, tax_code, customer_name,
      lines: list of {product_code, quantity, unit_price, line_total}
    """
    result = {
        "so_number":     "",
        "order_date":    None,
        "tax_code":      "",
        "customer_name": "",
        "lines":         [],
    }

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        header_parsed = False

        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables:
                continue

            for tbl_idx, table in enumerate(tables):
                if not table:
                    continue

                # Trang đầu, bảng đầu tiên chưa có header → bảng header đơn hàng
                if page_idx == 0 and tbl_idx == 0 and not header_parsed:
                    # Kiểm tra: nếu row[0][1] chứa "BH26" → đây là header table
                    first_row = table[0] if table else []
                    if first_row and len(first_row) >= 2 and "BH26" in str(first_row[1]).upper():
                        header_data = _parse_header_table(table)
                        result.update(header_data)
                        header_parsed = True
                        continue

                # Các bảng còn lại → bảng sản phẩm
                lines = _parse_product_table(table)
                result["lines"].extend(lines)

    return result


def parse_pdf_file(pdf_path) -> dict:
    """Đọc từ file path thay vì bytes."""
    with open(pdf_path, "rb") as f:
        return parse_pdf(f.read())
