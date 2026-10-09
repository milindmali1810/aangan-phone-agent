"""Tests WHEN the booking email is sent (fake Cal.com booking, fake email sender, real database; Telegram and HubSpot off).
   python tools/test_email_logic.py"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import calcom, db, emailer, hubspot, pipeline, telegram  # noqa: E402

telegram.enabled = lambda: False
hubspot.enabled = lambda: False
emailer.enabled = lambda: True
sent = []
emailer.send_booking = lambda name, slot, note, outcome: sent.append((name, slot, outcome)) or "fake-id"

src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = src.split('GOOD = """')[1].split('"""')[0]
NOT_FIT = src.split('NOT_FIT = """')[1].split('"""')[0]
now = lambda o=0: (datetime.now(timezone.utc) + timedelta(seconds=o)).isoformat()
FAKE = {"uid": "abcd1234efgh", "status": "accepted", "start": "2026-10-12T04:30:00.000Z", "createdAt": now()}


def call(n, transcript, booking):
    calcom.enabled = lambda: True
    calcom.find_consultation = lambda started, dur: booking
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    d = {"call_id": cid, "room_name": room}
    return pipeline.handle({"events": [
        {"event": "call_started", "timestamp": now(-60), "data": dict(d)},
        {"event": "call_ended", "timestamp": now(), "data": {**d, "call_duration": 60}},
        {"event": "call_postprocessing", "call_id": cid, "timestamp": now(), "data": {**d, "call_duration": 60, "transcript": transcript}}]})["processed"][0]


ok = True
def check(label, cond):
    global ok; ok &= bool(cond); print(("PASS  " if cond else "FAIL  ") + label)

try:
    r = call(1, GOOD, FAKE)
    check("booked + qualified: one email sent", len(sent) == 1 and r.get("email") == "fake-id")
    check("email carries the slot in India time", sent and sent[0][1] == "Mon 12 Oct, 10:00 AM IST")
    row = db.rest("GET", "calls?vaani_call_id=eq.TEST-call-1&select=consultation_booked,consultation_slot,handoff_note")[0]
    check("the call is recorded as booked, with the slot in the note", row["consultation_booked"] and "Mon 12 Oct, 10:00 AM IST" in row["handoff_note"])
    sent.clear()
    r = call(2, GOOD, None)
    check("qualified but NOT booked: no email", not sent and "email" not in r)
    r = call(3, NOT_FIT, FAKE)
    check("declined caller: no email, even if a booking existed", not sent and "email" not in r)
finally:
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print("test rows deleted")
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
