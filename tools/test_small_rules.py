"""Tests the office size limit and the big-project marker (no network, no database).   python tools/test_small_rules.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan.classifier import decide, is_big_project
from aangan import telegram

ok = True
def check(label, cond):
    global ok; ok &= bool(cond); print(("PASS  " if cond else "FAIL  ") + label)

def facts(kind, size):
    P = {"result": "pass", "evidence": ""}
    return {"is_complaint_or_existing_client": False, "is_unreachable": False, "scope_kind": kind, "size_sqft": size,
            "budget_lakh_min": None, "budget_lakh_max": None, "designed_area_sqft": None, "decision_maker_text": "", "weeks_until_deadline": None,
            "deadline_firm": None, "real_project": dict(P), "in_service_area": dict(P), "timeline": dict(P), "budget": dict(P), "decision_maker": dict(P)}

check("office of 4,000 sq ft is declined (limit 3,000)", decide(facts("office", 4000))[0] == "DECLINE")
check("the reason says why", "3,000" in decide(facts("office", 4000))[1])
check("office of exactly 3,000 sq ft still fits", decide(facts("office", 3000))[0] == "FORWARD")
check("office with no size given is not declined", decide(facts("office", None))[0] == "FORWARD")
check("a 5,000 sq ft VILLA is not declined by the office limit", decide(facts("full_home", 5000))[0] == "FORWARD")
check("big project: home over 3,000", is_big_project("full_home", 5500) and not is_big_project("full_home", 3000))
check("big project: office over 2,000", is_big_project("office", 2200) and not is_big_project("office", 2000))
check("single room is never 'big'", not is_big_project("single_room", 9000))
check("big project is marked at the top of the Telegram message", telegram.lead_text("FORWARD", "note", big=True).startswith("BIG PROJECT - tell Nikhil. NEW LEAD"))
check("not marked when small, and never on a decline", telegram.lead_text("FORWARD", "note").startswith("NEW LEAD") and telegram.lead_text("DECLINE", "n", "r", big=True).startswith("DECLINED"))
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
