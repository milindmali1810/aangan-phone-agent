"""Run the classifier on some or all enquiries.   python run_batch.py            (all 40)
                                                    python run_batch.py T10 F10 (just these)
Writes one JSON per enquiry to results/ and prints a summary table."""
import json
import sys
from pathlib import Path

from aangan.classifier import classify

root = Path(__file__).parent
ids = sys.argv[1:] or sorted(p.stem for p in (root / "enquiries").glob("*.txt"))
(root / "results").mkdir(exist_ok=True)
total = 0.0
for eid in ids:
    r = classify(eid)
    (root / "results" / f"{eid}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    total += r["cost_usd_estimate"]
    print(f"{eid}  {r['outcome']:<18} {r['reason'][:110]}")
print(f"\n{len(ids)} classified. Estimated Gemini cost: ${total:.4f}")
