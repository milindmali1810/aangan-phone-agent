"""ONE fake call through the LIVE internet address, checking the whole chain, then cleaning up everything it made:
classifier -> database -> Telegram (message is deleted afterwards) -> HubSpot (contact + deal deleted afterwards).
   python tools/test_live_chain.py https://aangan-webhook.vercel.app/api/vaani_webhook"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import db, env, hubspot, telegram  # noqa: E402

URL = sys.argv[1]
src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = (src.split('GOOD = """')[1].split('"""')[0]
        .replace("Rahul Deshmukh", "TEST Rahul Deshmukh")
        .replace("Nine eight two two one one two two three three", "Nine zero zero zero zero zero zero zero zero nine")
        .replace("Nine eight two two, one one two two, three three", "Nine zero zero zero, zero zero zero zero, zero nine"))
now = lambda o=0: (datetime.now(timezone.utc) + timedelta(seconds=o)).isoformat()
cid, room = "TEST-call-chain", "TEST-room-chain"
data = {"call_id": cid, "room_name": room}
body = {"events": [
    {"event": "call_started", "timestamp": now(-70), "data": dict(data)},
    {"event": "call_ended", "timestamp": now(), "data": {**data, "call_duration": 70}},
    {"event": "call_postprocessing", "call_id": cid, "timestamp": now(),
     "data": {**data, "call_duration": 70, "transcript": GOOD, "recording_url": "https://example.invalid/chain.mp3"}}]}
req = urllib.request.Request(URL + "?token=" + env.get("WEBHOOK_SECRET"), data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
msg_id = contact_id = deal_id = None
try:
    out = json.load(urllib.request.urlopen(req, timeout=120))
    r = out["processed"][0]
    print("server answered:", {k: v for k, v in r.items()})
    row = db.rest("GET", f"calls?vaani_call_id=eq.{cid}&select=*")[0]
    msg_id, contact_id, deal_id = row["telegram_message_id"], row["hubspot_contact_id"], row["hubspot_deal_id"]
    print("database : outcome", row["outcome"], "| notified_at set:", bool(row["designer_notified_at"]),
          "| hubspot ids saved:", bool(contact_id), bool(deal_id), "| errors:", row["hubspot_error"])
    print("telegram : message id", msg_id, "| error:", r.get("telegram_error"))
    if contact_id:
        c = hubspot.api("GET", f"/crm/v3/objects/contacts/{contact_id}?properties=firstname,lastname,phone,hs_lead_status")["properties"]
        print("hubspot  : contact", c["firstname"], c["lastname"], c["phone"], c["hs_lead_status"])
    if deal_id:
        d = hubspot.api("GET", f"/crm/v3/objects/deals/{deal_id}?properties=dealname,dealstage,hs_priority")["properties"]
        print("hubspot  : deal", d["dealname"], "| stage", d["dealstage"], "| priority", d["hs_priority"])
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
    if msg_id:
        try:
            telegram.api("deleteMessage", {"chat_id": env.get("TELEGRAM_CHAT_ID"), "message_id": msg_id})
        except Exception as e:
            print("could not delete the Telegram test message:", str(e)[:100])
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print("cleanup done: HubSpot contact/deal/notes, Telegram message and database rows removed")
