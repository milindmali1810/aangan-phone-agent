"""Tests the booking tools. Slots use the REAL Cal.com (read-only); booking uses a FAKE Cal.com so nothing is booked.
   python tools/test_booking_logic.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import booking

ok = True
def check(label, cond):
    global ok; ok &= bool(cond); print(("PASS  " if cond else "FAIL  ") + label)

# real, read-only
r = booking.available_slots()
check("real calendar: slots offered", r["available"] and len(r["slots"]) >= 3)
check("slots are spoken-friendly and carry an exact start", all(s["label"] and "T" in s["start"] and s["start"].endswith("+05:30") for s in r["slots"]))
check("no Sunday offered", not any("Sunday" in s["label"] for s in r["slots"]))
check("all inside 10:00-19:00 India time", all(10 <= int(s["start"][11:13]) < 19 for s in r["slots"]))
check("at most 3 times per day, at most 4 days", len(r["slots"]) <= 12)
print("   message:", r["message"][:230])

# fake Cal.com for booking
calls = []
def fake_ok(method, path, version, body=None):
    calls.append((method, path, body)); return {"data": {"uid": "abcd1234efgh", "start": body["start"]}}
booking._cal = fake_ok
res = booking.book("2026-10-12T10:30:00+05:30", "TEST Asha", "98 221 12233")
b = calls[-1][2]
check("booking succeeds with a plain-language confirmation", res["booked"] and "Monday 12 October at 10:30 AM" in res["message"])
check("time sent to Cal.com in UTC", b["start"] == "2026-10-12T05:00:00Z")
check("phone normalised to +91", b["attendee"]["phoneNumber"] == "+919822112233")
check("no email -> placeholder email so Cal.com accepts it", b["attendee"]["email"].endswith("@" + booking.NO_EMAIL_DOMAIN))
res2 = booking.book("2026-10-12T10:30:00+05:30", "TEST Asha", "9822112233", "asha@example.com")
check("real email is used when the caller gives one", calls[-1][2]["attendee"]["email"] == "asha@example.com")
check("missing name -> asked, nothing sent", (lambda n: booking.book("2026-10-12T10:30:00+05:30", "", "9822112233")["booked"] is False and len(calls) == n)(len(calls)))
check("bad time -> asked to use the exact value", booking.book("tomorrow morning", "TEST", "9822112233")["booked"] is False)
def fake_taken(method, path, version, body=None):
    if method == "POST": raise RuntimeError("400: This time slot is no longer available")
    return {"data": {"2026-10-12": [{"start": "2026-10-12T10:00:00.000+05:30"}]}}
booking._cal = fake_taken
res3 = booking.book("2026-10-12T10:30:00+05:30", "TEST Asha", "9822112233")
check("slot taken -> told so, with fresh times", res3["booked"] is False and "no longer free" in res3["message"] and res3["slots"])
def fake_down(method, path, version, body=None): raise RuntimeError("500: boom")
booking._cal = fake_down
res4 = booking.book("2026-10-12T10:30:00+05:30", "TEST Asha", "9822112233")
check("Cal.com down -> never promises a time", res4["booked"] is False and "designer will contact" in res4["message"])
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
