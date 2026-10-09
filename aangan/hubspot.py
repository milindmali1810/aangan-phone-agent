"""HubSpot: every caller becomes a contact (declines too, with the reason, so the rules can be audited later).
FORWARD and FORWARD_WITH_FLAG calls also become a deal carrying the handoff note.

- A repeat caller is found by phone number, never duplicated; each call adds a new note to the same contact.
- Never downgrades a contact: a later decline does not overwrite an earlier "Open" lead status.
- Safe to run twice for the same call: ids are stored on the call row and reused.
Needs HUBSPOT_TOKEN (a private-app token with contacts, deals and notes scopes, nothing else).
"""
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from . import config as C
from . import db, env

BASE = "https://api.hubapi.com"
# HubSpot's standard association type ids
NOTE_TO_CONTACT, NOTE_TO_DEAL, DEAL_TO_CONTACT = 202, 214, 3

LEAD_STATUS = {  # outcome -> HubSpot Lead Status value
    "FORWARD": "OPEN", "FORWARD_WITH_FLAG": "OPEN", "NEEDS_HUMAN": "IN_PROGRESS",
    "DECLINE": "UNQUALIFIED", "NOT_CLASSIFIED": "NEW",
}
TITLE = {
    "FORWARD": "NEW LEAD (passes all checks)", "FORWARD_WITH_FLAG": "NEW LEAD (has a flag)",
    "NEEDS_HUMAN": "NEEDS-HUMAN: complaint or existing client", "DECLINE": "DECLINED",
    "NOT_CLASSIFIED": "CALL BACK: no usable conversation",
}


def enabled():
    return bool(env.get("HUBSPOT_TOKEN"))


def api(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + env.get("HUBSPOT_TOKEN"), "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            raw = urllib.request.urlopen(req, timeout=20).read()
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:  # rate limited: wait and retry
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"HubSpot {method} {path} -> HTTP {e.code}: {e.read()[:300].decode()}")


def normalize_phone(raw):
    """Indian numbers to +91XXXXXXXXXX so the same caller always matches. Returns None if unusable."""
    if not raw or raw == "not given":
        return None
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("+") and len(digits) >= 11:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 11 and digits.startswith("0"):
        return "+91" + digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    return None


def _names(full):
    if not full or full == "not given":
        return "Unknown", "caller"
    parts = full.split()
    return parts[0], " ".join(parts[1:])


def find_contact(phone):
    r = api("POST", "/crm/v3/objects/contacts/search", {
        "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
        "properties": ["firstname", "lastname", "phone", "hs_lead_status"], "limit": 1})
    return r["results"][0] if r.get("results") else None


def _note(text, to_id, type_id):
    api("POST", "/crm/v3/objects/notes", {
        "properties": {"hs_timestamp": datetime.now(timezone.utc).isoformat(),
                       "hs_note_body": html.escape(text).replace("\n", "<br>")},
        "associations": [{"to": {"id": to_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": type_id}]}]})


def sync_call(saved, row):
    """Create/update the contact (+ deal) for one saved call. Returns what was done."""
    if saved.get("hubspot_contact_id"):  # same call delivered twice
        return {"skipped": "already synced"}
    outcome = row["outcome"]
    phone = normalize_phone(row["caller_phone"])
    if not phone and row["caller_name"] == "not given":
        return {"skipped": "no name and no phone: nothing to record"}

    first, last = _names(row["caller_name"])
    status = LEAD_STATUS[outcome]
    existing = find_contact(phone) if phone else None
    if existing:
        contact_id = existing["id"]
        # a repeat caller keeps their record; only a qualified call may move the status, never a decline
        if outcome in ("FORWARD", "FORWARD_WITH_FLAG", "NEEDS_HUMAN"):
            api("PATCH", f"/crm/v3/objects/contacts/{contact_id}", {"properties": {"hs_lead_status": status}})
        repeat = True
    else:
        props = {"firstname": first, "lastname": last, "lifecyclestage": "lead", "hs_lead_status": status}
        if phone:
            props["phone"] = phone
        if row["locality"] != "not given":
            props["city"] = row["locality"]
        contact_id = api("POST", "/crm/v3/objects/contacts", {"properties": props})["id"]
        repeat = False

    body = f"{TITLE[outcome]}\n\n{row['handoff_note'] or '(no details)'}"
    if outcome in ("DECLINE", "NEEDS_HUMAN", "NOT_CLASSIFIED"):
        body += f"\n\nReason: {row['reason']}"
    if repeat:
        body = "REPEAT CALLER\n\n" + body
    _note(body, contact_id, NOTE_TO_CONTACT)

    deal_id = None
    if outcome in ("FORWARD", "FORWARD_WITH_FLAG"):
        kind = row["property_type"].replace("_", " ")
        deal = api("POST", "/crm/v3/objects/deals", {
            "properties": {
                "dealname": f"{row['caller_name'] if row['caller_name'] != 'not given' else 'Unknown caller'}"
                            f" - {row['locality']} - {kind}",
                "pipeline": "default", "dealstage": C.HUBSPOT_DEAL_STAGE,
                "description": row["handoff_note"] or "",
                "hs_priority": "high" if row["referral"] != "not given" else "medium"},
            "associations": [{"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": DEAL_TO_CONTACT}]}]})
        deal_id = deal["id"]
        _note(body, deal_id, NOTE_TO_DEAL)

    db.rest("PATCH", f"calls?id=eq.{saved['id']}", {"hubspot_contact_id": contact_id, "hubspot_deal_id": deal_id, "hubspot_error": None})
    return {"contact": contact_id, "deal": deal_id, "repeat_caller": repeat}
