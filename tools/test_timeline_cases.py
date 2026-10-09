"""Eight synthetic enquiries that differ ONLY in what the caller says about time. Checks the classifier tells apart
a start date, a possession date, and a finish deadline, and whether that deadline is firm.   python tools/test_timeline_cases.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan.classifier import classify_text

BASE = """X1 · Phone · 9 October · 11:00am · 3 min
Front Desk: Good morning, Aangan Studio.
Caller: Hi, I'm Asha Sharma. I own a 3BHK flat in Baner, about 1200 square feet. I want the whole home designed and built. My husband and I decide together.
Front Desk: Lovely. And your timing?
Caller: {timing}
"""
CASES = [
    ("firm finish in a month (start tomorrow)", "I can start tomorrow, but I need it completely finished in one month. It is a fixed date, my parents are arriving from abroad.", "DECLINE"),
    ("flexible finish in a month", "I would like it finished in a month, but honestly I am flexible and can stretch it if needed.", "FORWARD_WITH_FLAG"),
    ("finish in a month, firmness not said", "I can start tomorrow and I want it completed in the next one month.", "FORWARD_WITH_FLAG"),
    ("start tomorrow, no finish date", "I would like to start as soon as possible, tomorrow if I can. I have no particular deadline for finishing.", "FORWARD"),
    ("possession next month, no finish date", "I get possession of the flat next month. We want to start the design now and there is no hurry to finish.", "FORWARD"),
    ("finish in three months", "We need it finished and ready to move in about three months from now, in January.", "FORWARD"),
    ("finish in 8 weeks, firm", "We must move in by the first of December, that is fixed because our lease ends.", "FORWARD_WITH_FLAG"),
    ("no timing at all", "I do not know yet, I am just starting to think about it.", "FORWARD_WITH_FLAG"),
]
ok = True
for name, timing, want in CASES:
    r = classify_text(BASE.format(timing=timing), "SYN")
    good = r["outcome"] == want
    ok &= good
    x = r["extracted"]
    print(("PASS  " if good else "FAIL  ") + f"{name:<42} -> {r['outcome']:<18} (wanted {want}) weeks={x.get('weeks_until_deadline')} firm={x.get('deadline_firm')}")
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
