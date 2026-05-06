"""
parse_eml.py
Trích xuất thông tin từ file .eml:
  - Header: From, Subject, Date, Message-ID
  - Body: MST đại lý (backup)
  - Attachment: bytes của file PDF đính kèm
"""

import email
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path


def _decode_str(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = ""
    for content, charset in parts:
        if isinstance(content, bytes):
            result += content.decode(charset or "utf-8", errors="replace")
        else:
            result += content
    return result.strip()


def _extract_so_number(subject: str) -> str:
    """Trích số đơn hàng BH26.XXXX từ subject."""
    match = re.search(r"BH26[._](\d+)", subject, re.IGNORECASE)
    if match:
        return f"BH26.{match.group(1)}"
    return ""


def _extract_mst_from_body(body: str) -> str:
    """Backup: trích MST từ body email."""
    match = re.search(r"MST\s*[:\|]\s*(\d{9,13})", body)
    if match:
        return match.group(1).strip()
    return ""


def parse_eml(eml_path: Path) -> dict:
    """
    Đọc file .eml và trả về dict:
      message_id, from_address, from_email, received_at,
      subject, so_number, attachment_name, pdf_bytes,
      body_mst (backup MST từ body)
    Trả về None nếu không tìm thấy PDF đính kèm.
    """
    with open(eml_path, "rb") as f:
        msg = email.message_from_bytes(f.read())

    subject = _decode_str(msg.get("Subject", ""))
    from_full = _decode_str(msg.get("From", ""))
    message_id = msg.get("Message-ID", "").strip()
    date_str = msg.get("Date", "")

    # Parse datetime
    try:
        received_at = parsedate_to_datetime(date_str)
    except Exception:
        received_at = None

    # Trích email address từ From
    email_match = re.search(r"<([^>]+)>", from_full)
    from_email = email_match.group(1) if email_match else from_full

    so_number = _extract_so_number(subject)
    pdf_bytes = None
    attachment_name = ""
    body_text = ""

    for part in msg.walk():
        content_type = part.get_content_type()

        # Thu thập body text để backup MST
        if content_type == "text/plain" and not body_text:
            payload = part.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="replace")

        # Lấy PDF đính kèm (chỉ lấy file đầu tiên)
        if content_type == "application/pdf" and pdf_bytes is None:
            pdf_bytes = part.get_payload(decode=True)
            raw_name = part.get_filename() or ""
            # Decode filename nếu encoded
            attachment_name = _decode_str(raw_name) if raw_name else f"{eml_path.stem}.pdf"

    if pdf_bytes is None:
        return None

    return {
        "message_id":       message_id,
        "from_address":     from_full,
        "from_email":       from_email,
        "received_at":      received_at,
        "subject":          subject,
        "so_number_email":  so_number,          # so_number trích từ subject
        "attachment_name":  attachment_name,
        "pdf_bytes":        pdf_bytes,
        "body_mst":         _extract_mst_from_body(body_text),
    }
