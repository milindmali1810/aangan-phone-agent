"""Load the 40 September enquiries + their classifier results into Supabase as SAMPLE rows.

Needs in .env:  SUPABASE_URL  and  SUPABASE_SECRET_KEY   (the secret key can write to locked tables)
Run:            python tools/seed_supabase.py
Safe to re-run: rows are matched on source_id and updated, not duplicated.

Times come only from the transcripts. Where a transcript doesn't say when the studio replied
(web forms, complaints), response_tracked is set to false so the dashboard doesn't count it.
"""
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))
MONTHS = {"Sept": 9, "September": 9}


def env(name):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} is missing from .env")


URL, KEY = env("SUPABASE_URL").rstrip("/"), env("SUPABASE_SECRET_KEY")


def call(method, path, body=None, prefer=None):
    h = {"apikey": KEY, "Content-Type": "application/json"}
    if not KEY.startswith("sb_secret_"):
        h["Authorization"] = "Bearer " + KEY
    if prefer:
        h["Prefer"] = prefer
    req = urllib.request.Request(URL + "/rest/v1/" + path, method=method, headers=h,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
        return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read()[:400].decode()}")


def stamp(day, hh, mm, ap):
    h = int(hh) % 12 + (12 if ap == "pm" else 0)
    return datetime(2026, 9, int(day), h, int(mm), tzinfo=IST)


def times(eid, text):
    """Returns (started, first_response, seconds, response_tracked)."""
    first = text.splitlines()[0]
    if eid.startswith("T"):
        m = re.search(r"(\d{1,2}) September · (\d{1,2}):(\d{2})(am|pm)", first)
        started = stamp(*m.groups())
        if "MISSED" in first:
            return started, None, None, True
        secs = sum(int(a) * (60 if u == "min" else 1) for a, u in re.findall(r"(\d+) (min|sec)", first))
        if eid == "T17":
            secs = 72 + 270  # two calls: 1m12s dropped + 4m30s
        return started, started, secs or None, True  # answered live by the front desk
    if eid.startswith("W"):
        msgs = re.findall(r"^(\d{1,2}) Sept, (\d{1,2}):(\d{2})(am|pm)(?: \([A-Za-z]+\))? —\s+([^:\n]+):", text, re.M)
        started = stamp(*msgs[0][:4])
        reply = next((stamp(*m[:4]) for m in msgs if m[4].strip() == "Front Desk"), None)
        return started, reply, None, True
    m = re.search(r"(\d{1,2}) September · (\d{1,2}):(\d{2})(am|pm)", first)  # web form
    return stamp(*m.groups()), None, None, False


def clean(v):
    return "not given" if v in (None, "", "not given", "Not given") else v


rows, costs = [], {}
for p in sorted((ROOT / "results").glob("*.json")):
    r = json.loads(p.read_text(encoding="utf-8"))
    eid = r["id"]
    text = (ROOT / "enquiries" / f"{eid}.txt").read_text(encoding="utf-8")
    x = r["extracted"]
    started, replied, secs, tracked = times(eid, text)
    if r["outcome"] == "NEEDS_HUMAN":
        tracked = False  # a complaint is not a new enquiry; its reply time would distort the numbers
    rows.append({
        "source_id": eid,
        "channel": {"T": "phone", "W": "whatsapp", "F": "web_form"}[eid[0]],
        "is_sample": True,
        "caller_name": clean(x.get("caller_name")), "caller_phone": clean(x.get("phone")),
        "locality": clean(x.get("locality")), "property_type": x.get("scope_kind") or "not_given",
        "scope_summary": clean(x.get("scope_summary")), "size_sqft": x.get("size_sqft"),
        "timeline_text": clean(x.get("timeline_text")), "decision_maker_text": clean(x.get("decision_maker_text")),
        "budget_lakh_min": x.get("budget_lakh_min"), "budget_lakh_max": x.get("budget_lakh_max"),
        "referral": clean(x.get("referral")), "site_status": clean(x.get("site_status")),
        "owner_or_tenant": clean(x.get("owner_or_tenant")), "language": clean(x.get("language")),
        "asked_about_price": x.get("asked_about_price"),
        "transcript": text,
        "outcome": r["outcome"], "reason": r["reason"], "flags": r["flags"], "criteria": r["criteria"],
        "handoff_note": r["handoff_note"], "needs_human": r["outcome"] == "NEEDS_HUMAN",
        "call_started_at": started.isoformat(),
        "first_response_at": replied.isoformat() if replied else None,
        "response_tracked": tracked,
        "call_seconds": secs,
        "classification_cost_usd": r["cost_usd_estimate"],
    })
    costs[eid] = r

saved = call("POST", "calls?on_conflict=source_id", rows, "resolution=merge-duplicates,return=representation")
ids = {row["source_id"]: row["id"] for row in saved}

# one cost_log row per classification (delete the old ones first so re-runs don't double count)
call("DELETE", "cost_log?call_id=in.(" + ",".join(ids.values()) + ")")
call("POST", "cost_log", [{
    "call_id": ids[eid], "kind": "classification", "amount_usd": r["cost_usd_estimate"],
    "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"], "model": r["model"],
} for eid, r in costs.items()])
print(f"Seeded {len(saved)} calls and {len(costs)} cost rows.")
