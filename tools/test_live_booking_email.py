"""Proves the LIVE chain after a booking WITHOUT spending Vaani credit:
 1. makes a real Cal.com booking itself (tagged team mailbox as the attendee email, like the agent does),
 2. sends the live webhook a fake call that overlaps it,
 3. checks the booking was found, the slot is in the note, the email was sent, HubSpot and the dashboard agree,
 4. cleans everything up (cancels the booking, deletes HubSpot and database test records, deletes the Telegram test messages).
   python tools/test_live_booking_email.py"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import booking, calcom, db, env, hubspot, telegram  # noqa: E402

URL = "https://aangan-webhook.vercel.app/api/vaani_webhook"
src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = (src.split('GOOD = """')[1].split('"""')[0]
        .replace("Rahul Deshmukh", "TEST Rahul Deshmukh")
        .replace("Nine eight two two one one two two three three", "Nine zero zero zero zero zero zero zero zero eight")
        .replace("Nine eight two two, one one two two, three three", "Nine zero zero zero, zero zero zero zero, zero eight"))
now = lambda o=0: (datetime.now(timezone.utc) + timedelta(seconds=o)).isoformat()
uid = contact_id = deal_id = msg_id = None
try:
    # 1. a real booking, on the first free slot Cal.com itself offers
    first = booking.available_slots()["slots"][0]
    start_utc = datetime.fromisoformat(first["start"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = booking._cal("POST", "/v2/bookings", "2024-08-13", {
        "start": start_utc, "eventTypeId": booking.C.CAL_EVENT_TYPE_ID,
        "attendee": {"name": "TEST Rahul Deshmukh (delete)", "email": booking._fallback_email("9000000008"), "timeZone": "Asia/Kolkata", "phoneNumber": "+919000000008", "language": "en"},
        "metadata": {"source": "aangan-diagnostic"}})["data"]
    uid = res["uid"]
    print("1. real Cal.com booking made:", first["label"], "| uid", uid, "| status", res.get("status"))

    # 2. a fake call that overlaps it, sent to the LIVE webhook
    cid, room = "TEST-call-bookemail", "TEST-room-bookemail"
    d = {"call_id": cid, "room_name": room}
    body = {"events": [
        {"event": "call_started", "timestamp": now(-75), "data": dict(d)},
        {"event": "call_ended", "timestamp": now(), "data": {**d, "call_duration": 75}},
        {"event": "call_postprocessing", "call_id": cid, "timestamp": now(),
         "data": {**d, "call_duration": 75, "transcript": GOOD, "recording_url": "https://example.invalid/booked.mp3"}}]}
    req = urllib.request.Request(URL + "?token=" + env.get("WEBHOOK_SECRET"), data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    out = json.load(urllib.request.urlopen(req, timeout=120))["processed"][0]
    print("2. live server answered:", {k: v for k, v in out.items() if k != "row_id"})

    # 3. what the live system did
    row = db.rest("GET", f"calls?vaani_call_id=eq.{cid}&select=*")[0]
    msg_id, contact_id, deal_id = row["telegram_message_id"], row["hubspot_contact_id"], row["hubspot_deal_id"]
    print("3a. booking found and recorded:", row["consultation_booked"], "| slot:", row["consultation_slot"])
    print("3b. slot in the designer note:", "Consultation slot: " in row["handoff_note"] and "not booked" not in row["handoff_note"], "|", [l for l in row["handoff_note"].split("\n") if l.startswith("Consultation")][0])
    print("3c. email sent by the live server:", out.get("email") or ("NOT SENT " + str(out.get("email_error"))))
    print("3d. Telegram lead posted:", bool(msg_id), "| HubSpot contact + deal:", bool(contact_id), bool(deal_id))
    if out.get("email"):
        print("EMAIL_ID", out["email"])
    det = json.load(urllib.request.urlopen(urllib.request.Request(f"https://aangan-webhook.vercel.app/api/calls?id={row['id']}", headers={"X-Dashboard-Key": env.get("DASHBOARD_PASSWORD")}), timeout=30))
    print("3e. dashboard shows it as booked:", det["consultation_booked"], "| transcript chars:", len(det["transcript"]))
finally:
    notes = set()
    for obj, oid in (("contacts", contact_id), ("deals", deal_id)):
        if oid:
            notes |= {x["toObjectId"] for x in hubspot.api("GET", f"/crm/v4/objects/{obj}/{oid}/associations/notes").get("results", [])}
    for nid in notes:
        hubspot.api("DELETE", f"/crm/v3/objects/notes/{nid}")
    if deal_id:
        hubspot.api("DELETE", f"/crm/v3/objects/deals/{deal_id}")
    if contact_id:
        hubspot.api("DELETE", f"/crm/v3/objects/contacts/{contact_id}")
    if msg_id:  # the lead and its transcript reply (sent straight after it)
        for m in (msg_id, msg_id + 1):
            try:
                telegram.api("deleteMessage", {"chat_id": env.get("TELEGRAM_CHAT_ID"), "message_id": m})
            except Exception:
                pass
    if uid:
        booking._cal("POST", f"/v2/bookings/{uid}/cancel", "2024-08-13", {"cancellationReason": "diagnostic test, please ignore"})
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print("4. cleanup done: Cal.com booking cancelled; HubSpot, Telegram and database test records removed")
