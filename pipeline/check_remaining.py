import sys, io, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from collections import Counter

logs = sorted(glob.glob("logs/errors_*.json"))
with open(logs[-1], encoding="utf-8") as f:
    errors = json.load(f)

print(f"Remaining errors: {len(errors)}")
errs = Counter()
for e in errors:
    msg = e["error"]
    if "MST=" in msg:
        errs["no_customer"] += 1
    elif "không tồn tại trong DB" in msg or "Mã hàng" in msg:
        errs["invalid_product"] += 1
    else:
        errs[e["stage"]] += 1
print("By type:", dict(errs))
print()
print("Sample errors:")
for e in errors[:10]:
    fname = e["file"]
    err   = e["error"]
    print(f"  {fname}: {err[:110]}")
