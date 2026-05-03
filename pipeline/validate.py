"""
validate.py
Các rule kiểm tra dữ liệu trước khi ghi vào database.
Trả về list[str] lỗi (rỗng = hợp lệ).
"""

from config import AMOUNT_TOLERANCE


def validate_order(eml_data: dict, pdf_data: dict, valid_products: set,
                   existing_so_numbers: set) -> list[str]:
    """
    Kiểm tra toàn bộ 1 đơn hàng.

    Args:
        eml_data:          dict từ parse_eml()
        pdf_data:          dict từ parse_pdf()
        valid_products:    set mã hàng hợp lệ trong DB (product.product_code)
        existing_so_numbers: set so_number đã có trong sales_order

    Returns:
        list lỗi - nếu rỗng thì hợp lệ
    """
    errors = []

    # ── 1. Số đơn hàng ───────────────────────────────────────────────────────
    so_number = pdf_data.get("so_number") or eml_data.get("so_number_email", "")
    if not so_number:
        errors.append("Không trích được số đơn hàng (so_number)")
        return errors  # fatal - không cần check tiếp

    if so_number in existing_so_numbers:
        errors.append(f"Đơn hàng {so_number} đã tồn tại trong database (duplicate)")
        return errors

    # ── 2. Ngày đặt hàng ─────────────────────────────────────────────────────
    order_date = pdf_data.get("order_date")
    if order_date is None:
        errors.append("Không đọc được ngày đặt hàng")
    else:
        if order_date.year != 2026 or order_date.month != 3:
            errors.append(f"Ngày đặt hàng {order_date} không thuộc tháng 3/2026")

    # ── 3. Khách hàng ────────────────────────────────────────────────────────
    if not pdf_data.get("tax_code") and not eml_data.get("body_mst"):
        errors.append("Không tìm thấy MST đại lý trong PDF hoặc email body")

    # customer_code được tra từ DB bên ngoài; nếu truyền vào None = không tìm thấy
    # Kiểm tra này được thực hiện ở db_writer sau khi lookup

    # ── 4. Dòng sản phẩm ─────────────────────────────────────────────────────
    lines = pdf_data.get("lines", [])
    if not lines:
        errors.append("Không có dòng sản phẩm nào được trích xuất")
        return errors

    invalid_codes = []
    for i, line in enumerate(lines, start=1):
        code = line.get("product_code", "")
        qty = line.get("quantity", 0)
        unit_price = line.get("unit_price", 0)
        line_total = line.get("line_total", 0)

        # 4a. Mã hàng tồn tại
        if code not in valid_products:
            invalid_codes.append(code)

        # 4b. Số lượng > 0
        if qty <= 0:
            errors.append(f"Dòng {i} ({code}): Số lượng phải > 0, nhận được {qty}")

        # 4c. Đơn giá >= 0
        if unit_price < 0:
            errors.append(f"Dòng {i} ({code}): Đơn giá âm ({unit_price})")

        # 4d. Kiểm tra thành tiền = qty × đơn giá
        # Dùng absolute tolerance (VND) HOẶC relative tolerance (0.01%)
        # để xử lý cả trường hợp giá lẻ thập phân × số lượng lớn
        if unit_price > 0 and qty > 0:
            expected = qty * unit_price
            abs_diff = abs(expected - line_total)
            rel_diff = abs_diff / line_total if line_total > 0 else abs_diff
            if abs_diff > AMOUNT_TOLERANCE and rel_diff > 0.0001:
                errors.append(
                    f"Dòng {i} ({code}): Thành tiền không khớp "
                    f"({qty} × {unit_price} = {expected:.0f}, nhưng PDF ghi {line_total:.0f})"
                )

    if invalid_codes:
        errors.append(f"Mã hàng không tồn tại trong DB: {', '.join(invalid_codes)}")

    return errors
