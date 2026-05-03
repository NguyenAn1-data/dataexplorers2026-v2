"""Test nhanh parse_eml + parse_pdf trên 3 file mẫu."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from parse_eml import parse_eml
from parse_pdf import parse_pdf
from pathlib import Path

EML_FOLDER = Path(r"d:\Data explore vòng 2\Emails & Files\tnbike_emails_mar2026")
TEST_FILES = ["BH26_0935.eml", "BH26_0939.eml", "BH26_1010.eml"]

for fname in TEST_FILES:
    path = EML_FOLDER / fname
    if not path.exists():
        print(f"{fname}: NOT FOUND")
        continue

    eml = parse_eml(path)
    if eml is None:
        print(f"{fname}: No PDF attachment")
        continue

    pdf = parse_pdf(eml["pdf_bytes"])
    so  = pdf.get("so_number") or eml.get("so_number_email", "")

    print(f"--- {fname} ---")
    print(f"  message_id : {eml['message_id']}")
    print(f"  from       : {eml['from_address'][:60]}")
    print(f"  so_number  : {so}")
    print(f"  order_date : {pdf['order_date']}")
    print(f"  tax_code   : {pdf['tax_code']}")
    print(f"  lines      : {len(pdf['lines'])} dong")
    total = sum(ln["line_total"] for ln in pdf["lines"])
    print(f"  total_amt  : {total:,.0f}")
    if pdf["lines"]:
        ln0 = pdf["lines"][0]
        print(f"  line[0]    : code={ln0['product_code']} qty={ln0['quantity']} price={ln0['unit_price']:,.0f} total={ln0['line_total']:,.0f}")
    print()
