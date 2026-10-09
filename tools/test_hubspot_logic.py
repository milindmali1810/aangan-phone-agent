"""Tests the HubSpot rules with a FAKE HubSpot (in memory) and the REAL database.
Creates TEST- rows and deletes them at the end.   python tools/test_hubspot_logic.py
A final test against the real HubSpot API needs HUBSPOT_TOKEN and is done separately."""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HUBSPOT_TOKEN"] = "fake"

from aangan import db, hubspot, pipeline, telegram  # noqa: E402

telegram.enabled = lambda: False  # never post to the real Telegram group from a test

store = {"contacts": {}, "deals": {}, "notes": []}
log = []


def fake_api(method, path, body=None):
    log.append((method, path))
    if path.endswith("/contacts/search"):
        want = body["filterGroups"][0]["filters"][0]["value"]
        hits = [{"id": i, "properties": c} for i, c in store["contacts"].items() if c.get("phone") == want]
        return {"results": hits[:1]}
    if path == "/crm/v3/objects/contacts":
        cid = str(100 + len(store["contacts"]))
        store["contacts"][cid] = dict(body["properties"])
        return {"id": cid}
    if path.startswith("/crm/v3/objects/contacts/") and method == "PATCH":
        store["contacts"][path.rsplit("/", 1)[1]].update(body["properties"])
        return {}
    if path == "/crm/v3/objects/deals":
        did = str(500 + len(store["deals"]))
        store["deals"][did] = {**body["properties"], "assoc": body["associations"]}
        return {"id": did}
    if path == "/crm/v3/objects/notes":
        store["notes"].append({"text": body["properties"]["hs_note_body"], "to": body["associations"][0]["to"]["id"]})
        return {"id": str(900 + len(store["notes"]))}
    raise AssertionError("unexpected call " + method + " " + path)


hubspot.api = fake_api
src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = src.split('GOOD = """')[1].split('"""')[0]
NOT_FIT = src.split('NOT_FIT = """')[1].split('"""')[0]
now = lambda o=0: (datetime.now(timezone.utc) + timedelta(seconds=o)).isoformat()


def make_call(n, transcript, phone="+919800000001"):
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    data = {"call_id": cid, "room_name": room}
    if phone:
        data["phone_number"] = phone
    ev = [{"event": "call_started", "timestamp": now(-60), "data": dict(data)},
          {"event": "call_ended", "timestamp": now(), "data": {**data, "call_duration": 60}},
          {"event": "call_postprocessing", "call_id": cid, "timestamp": now(),
           "data": {**data, "call_duration": 60, "transcript": transcript, "recording_url": "https://example.invalid/r.mp3"}}]
    return pipeline.handle({"events": ev})["processed"][0]


ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + label)


try:
    check("phone: 10 digits -> +91", hubspot.normalize_phone("9822112233") == "+919822112233")
    check("phone: 0 prefix -> +91", hubspot.normalize_phone("09822112233") == "+919822112233")
    check("phone: 91 prefix -> +91", hubspot.normalize_phone("919822112233") == "+919822112233")
    check("phone: spaces and dashes", hubspot.normalize_phone("98221-12233") == "+919822112233")
    check("phone: 'not given' and junk -> None", hubspot.normalize_phone("not given") is None and hubspot.normalize_phone("12345") is None)

    # 1. good lead: contact + deal + notes, associated
    r1 = make_call(1, GOOD)
    c = list(store["contacts"].values())
    check("good lead: one contact created, Open, with phone and city",
          len(c) == 1 and c[0]["hs_lead_status"] == "OPEN" and c[0]["phone"] == "+919822112233" and c[0]["city"] == "Baner")
    check("good lead: name split into first and last", c[0]["firstname"] == "Rahul" and c[0]["lastname"] == "Deshmukh")
    check("good lead: one deal, in the default pipeline, linked to the contact, priority high (referral)",
          len(store["deals"]) == 1 and list(store["deals"].values())[0]["pipeline"] == "default"
          and list(store["deals"].values())[0]["assoc"][0]["to"]["id"] == "100" and list(store["deals"].values())[0]["hs_priority"] == "high")
    check("good lead: deal carries the handoff note, no price anywhere", "Rahul Deshmukh" in list(store["deals"].values())[0]["description"]
          and "lakh" not in list(store["deals"].values())[0]["description"].lower())
    check("good lead: notes on contact and deal", len(store["notes"]) == 2)
    row = db.rest("GET", "calls?vaani_call_id=eq.TEST-call-1&select=hubspot_contact_id,hubspot_deal_id,hubspot_error")[0]
    check("ids saved on the call row", row["hubspot_contact_id"] == "100" and row["hubspot_deal_id"] == "500" and row["hubspot_error"] is None)

    # 2. same call delivered again: nothing new
    before = (len(store["contacts"]), len(store["deals"]), len(store["notes"]))
    make_call(1, GOOD)
    check("re-delivery: no new contact, deal or note", before == (len(store["contacts"]), len(store["deals"]), len(store["notes"])))

    # 3. repeat caller who is then declined: same contact, not downgraded, no deal
    make_call(2, NOT_FIT, phone="+919822112233")
    check("repeat caller: still one contact", len(store["contacts"]) == 1)
    check("repeat caller: Open status NOT overwritten by a decline", store["contacts"]["100"]["hs_lead_status"] == "OPEN")
    check("repeat caller: still one deal", len(store["deals"]) == 1)
    check("repeat caller: new note marked REPEAT CALLER", any("REPEAT CALLER" in n["text"] for n in store["notes"]))

    # 4. a decline from a new number: contact Unqualified, reason in the note, no deal
    make_call(3, NOT_FIT, phone="+919800000003")
    new = [c for c in store["contacts"].values() if c.get("phone") == "+919800000003"]
    check("decline: contact created as Unqualified", len(new) == 1 and new[0]["hs_lead_status"] == "UNQUALIFIED")
    check("decline: reason written in the note", any("Reason:" in n["text"] and "Nashik" in n["text"] for n in store["notes"]))
    check("decline: no deal", len(store["deals"]) == 1)

    # 5. nothing known at all: no junk contact
    n_before = len(store["contacts"])
    make_call(4, "", phone=None)
    check("no name, no phone: no contact created", len(store["contacts"]) == n_before)
finally:
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print("test rows deleted")
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
