"""Debug 2 file PDF không extract được product lines."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
import pdfplumber
from pathlib import Path
from parse_eml import parse_eml

EML_FOLDER = Path(r"d:\Data explore vòng 2\Emails & Files\tnbike_emails_mar2026")

for fname in ["BH26_1561.eml", "BH26_1564.eml"]:
    print(f"\n=== {fname} ===")
    eml = parse_eml(EML_FOLDER / fname)
    if not eml:
        print("No PDF")
        continue
    import io as _io
    with pdfplumber.open(_io.BytesIO(eml["pdf_bytes"])) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            text   = page.extract_text()
            print(f"  Page {i+1}: {len(tables)} tables")
            print(f"  Text preview: {repr(text[:200]) if text else 'EMPTY'}")
            for j, t in enumerate(tables):
                print(f"    Table {j}: {len(t)} rows")
                for row in t[:4]:
                    print(f"      {row}")
