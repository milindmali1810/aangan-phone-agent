"""REAL HubSpot test with clearly fake callers (names start with TEST, phones +91900000000x).
Telegram is switched off. Everything it creates is deleted at the end.   python tools/test_hubspot_real.py"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import db, hubspot, pipeline, telegram  # noqa: E402

telegram.enabled = lambda: False
src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = (src.split('GOOD = """')[1].split('"""')[0]
        .replace("Rahul Deshmukh", "TEST Rahul Deshmukh")
        .replace("Nine eight two two one one two two three three", "Nine zero zero zero zero zero zero zero zero one")
        .replace("Nine eight two two, one one two two, three three", "Nine zero zero zero, zero zero zero zero, zero one"))
NOT_FIT = src.split('NOT_FIT = """')[1].split('"""')[0].replace("Mahesh Pawar", "TEST Mahesh Pawar")
now = lambda o=0: (datetime.now(timezone.utc) + timedelta(seconds=o)).isoformat()


def make_call(n, transcript, phone=None):
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    data = {"call_id": cid, "room_name": room}
    if phone:
        data["phone_number"] = phone
    return pipeline.handle({"events": [
        {"event": "call_started", "timestamp": now(-60), "data": dict(data)},
        {"event": "call_ended", "timestamp": now(), "data": {**data, "call_duration": 60}},
        {"event": "call_postprocessing", "call_id": cid, "timestamp": now(),
         "data": {**data, "call_duration": 60, "transcript": transcript, "recording_url": "https://example.invalid/r.mp3"}}]})["processed"][0]


def contact(phone):
    return hubspot.find_contact(phone)


def assoc(obj, oid, to):
    return [x["toObjectId"] for x in hubspot.api("GET", f"/crm/v4/objects/{obj}/{oid}/associations/{to}").get("results", [])]


created = {"contacts": set(), "deals": set()}
try:
    r1 = make_call(1, GOOD)
    print("call 1 (good lead)        ->", r1.get("outcome"), r1.get("hubspot"), r1.get("hubspot_error", ""))
    r2 = make_call(2, NOT_FIT, phone="+919000000001")
    print("call 2 (same phone, decline) ->", r2.get("outcome"), r2.get("hubspot"), r2.get("hubspot_error", ""))
    r3 = make_call(3, NOT_FIT, phone="+919000000003")
    print("call 3 (new phone, decline)  ->", r3.get("outcome"), r3.get("hubspot"), r3.get("hubspot_error", ""))
    r1b = make_call(1, GOOD)
    print("call 1 again (re-delivery)   ->", r1b.get("hubspot"), r1b.get("hubspot_error", ""))

    for ph in ("+919000000001", "+919000000003"):
        c = contact(ph)
        if c:
            created["contacts"].add(c["id"])
    for row in db.rest("GET", "calls?vaani_call_id=like.TEST-*&select=hubspot_contact_id,hubspot_deal_id"):
        if row["hubspot_contact_id"]:
            created["contacts"].add(row["hubspot_contact_id"])
        if row["hubspot_deal_id"]:
            created["deals"].add(row["hubspot_deal_id"])
    print("\n--- what is now in HubSpot ---")
    for cid in sorted(created["contacts"]):
        c = hubspot.api("GET", f"/crm/v3/objects/contacts/{cid}?properties=firstname,lastname,phone,city,hs_lead_status,lifecyclestage")["properties"]
        print(f"contact {cid}: {c['firstname']} {c['lastname']} | {c['phone']} | {c.get('city')} | status {c['hs_lead_status']} | {c['lifecyclestage']}")
        print("   linked deals:", assoc("contacts", cid, "deals"), "| notes:", len(assoc("contacts", cid, "notes")))
    for did in sorted(created["deals"]):
        d = hubspot.api("GET", f"/crm/v3/objects/deals/{did}?properties=dealname,dealstage,pipeline,hs_priority,description")["properties"]
        print(f"deal {did}: {d['dealname']} | stage {d['dealstage']} | pipeline {d['pipeline']} | priority {d['hs_priority']}")
        print("   linked contacts:", assoc("deals", did, "contacts"), "| notes:", len(assoc("deals", did, "notes")))
        print("   description starts:", (d["description"] or "")[:70].replace("\n", " | "))
finally:
    notes = set()
    for cid in created["contacts"]:
        notes |= set(assoc("contacts", cid, "notes"))
    for did in created["deals"]:
        notes |= set(assoc("deals", did, "notes"))
    failed = []
    for nid in notes:
        try:
            hubspot.api("DELETE", f"/crm/v3/objects/notes/{nid}")
        except Exception as e:
            failed.append(("note", nid, str(e)[:80]))
    for did in created["deals"]:
        try:
            hubspot.api("DELETE", f"/crm/v3/objects/deals/{did}")
        except Exception as e:
            failed.append(("deal", did, str(e)[:80]))
    for cid in created["contacts"]:
        try:
            hubspot.api("DELETE", f"/crm/v3/objects/contacts/{cid}")
        except Exception as e:
            failed.append(("contact", cid, str(e)[:80]))
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print(f"\ncleanup: deleted {len(notes)} notes, {len(created['deals'])} deals, {len(created['contacts'])} contacts; failures: {failed or 'none'}")
