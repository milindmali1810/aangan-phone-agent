"""What happens when Vaani tells us about a call.

call_started etc.  -> remembered in call_events (so we can MEASURE when the call began)
call_postprocessing -> classify the transcript, save the call + its costs.
HubSpot and Telegram steps plug in at the marked place once those phases are built.
"""
import hmac
from datetime import datetime, timedelta, timezone

from . import config as C
from . import db, env
from .classifier import classify_text

IST = timezone(timedelta(hours=5, minutes=30))
START_EVENTS = ("call_started", "user_picked_up_at")


def token_ok(token):
    secret = env.get("WEBHOOK_SECRET")
    return bool(secret) and hmac.compare_digest(token or "", secret)


def _parse_ts(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _start_time(room, event_ts, duration_ms):
    """Prefer the time we received call_started. Otherwise work backwards from the event time and duration."""
    if room:
        rows = db.rest("GET", f"call_events?room_name=eq.{room}&event=in.({','.join(START_EVENTS)})"
                              "&order=received_at.asc&limit=1&select=received_at")
        if rows:
            return _parse_ts(rows[0]["received_at"]), "event"
    end = _parse_ts(event_ts) or datetime.now(timezone.utc)
    return end - timedelta(milliseconds=duration_ms or 0), "estimated"


def _clean(v):
    return "not given" if v in (None, "", "not given", "Not given") else v


def handle(payload):
    event = payload.get("event", "unknown")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    room, call_id = data.get("room_name"), payload.get("call_id") or data.get("call_id")
    db.rest("POST", "call_events", {"room_name": room, "vaani_call_id": call_id, "event": event, "payload": payload})
    if event != "call_postprocessing":
        return {"ok": True, "stored_event": event}

    transcript = (data.get("transcript") or "").strip()
    duration_ms = data.get("call_duration") or 0
    started, source = _start_time(room, payload.get("timestamp"), duration_ms)
    stamp = started.astimezone(IST).strftime("%d %B %Y · %I:%M%p")

    if len(transcript) < 20 or "not available" in transcript.lower():
        # nothing was said: do not spend an AI call, but still record that it happened
        r = {"outcome": "NOT_CLASSIFIED", "reason": "Call connected but no usable conversation; call back.",
             "flags": [], "criteria": None, "handoff_note": None, "tokens_in": 0, "tokens_out": 0,
             "cost_usd_estimate": 0.0, "model": None, "extracted": {}}
        transcript = transcript or "(no transcript)"
    else:
        r = classify_text(f"{call_id} · Phone · {stamp} (live call with the voice agent)\n" + transcript, call_id or "live")

    if r["handoff_note"]:  # live calls have no transcript file; point at the call itself
        r["handoff_note"] = "\n".join(
            f"Call: {call_id} | Recording: {data.get('recording_url') or 'not available'}" if l.startswith("Transcript:") else l
            for l in r["handoff_note"].split("\n"))
    x = r["extracted"]
    voice_usd = (duration_ms / 60000) * C.VOICE_RATE_INR_PER_MIN / C.INR_PER_USD
    row = {
        "vaani_call_id": call_id, "vaani_room_name": room, "channel": "phone", "is_sample": False,
        "caller_name": _clean(x.get("caller_name")), "caller_phone": _clean(x.get("phone")),
        "locality": _clean(x.get("locality")), "property_type": x.get("scope_kind") or "not_given",
        "scope_summary": _clean(x.get("scope_summary")), "size_sqft": x.get("size_sqft"),
        "timeline_text": _clean(x.get("timeline_text")), "decision_maker_text": _clean(x.get("decision_maker_text")),
        "budget_lakh_min": x.get("budget_lakh_min"), "budget_lakh_max": x.get("budget_lakh_max"),
        "referral": _clean(x.get("referral")), "site_status": _clean(x.get("site_status")),
        "owner_or_tenant": _clean(x.get("owner_or_tenant")), "language": _clean(x.get("language")),
        "household_notes": _clean(x.get("household_notes")), "headcount": x.get("headcount"),
        "rooms_wanted": _clean(x.get("rooms_wanted")), "contact_preference": _clean(x.get("contact_preference")),
        "business_description": _clean(x.get("business_description")),
        "asked_about_price": x.get("asked_about_price"),
        "transcript": transcript, "recording_url": data.get("recording_url"),
        "vaani_summary": data.get("summary"), "end_reason": data.get("end_reason"),
        "outcome": r["outcome"], "reason": r["reason"], "flags": r["flags"], "criteria": r["criteria"],
        "handoff_note": r["handoff_note"], "needs_human": r["outcome"] == "NEEDS_HUMAN",
        "call_started_at": started.isoformat(), "started_at_source": source,
        # the voice agent greets the moment the call connects (let_user_speak_first is off)
        "first_response_at": started.isoformat(), "response_tracked": True,
        "call_seconds": round(duration_ms / 1000) if duration_ms else None,
        "voice_cost_usd": round(voice_usd, 6), "classification_cost_usd": r["cost_usd_estimate"],
    }
    saved = db.rest("POST", "calls?on_conflict=vaani_call_id", [row],
                    "resolution=merge-duplicates,return=representation")[0]
    db.rest("DELETE", f"cost_log?call_id=eq.{saved['id']}")  # re-delivery must not double count
    db.rest("POST", "cost_log", [
        {"call_id": saved["id"], "kind": "voice", "amount_usd": round(voice_usd, 6),
         "tokens_in": None, "tokens_out": None, "model": "vaani"},
        {"call_id": saved["id"], "kind": "classification", "amount_usd": r["cost_usd_estimate"],
         "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"], "model": r["model"]},
    ])

    # --- later phases plug in here, using `saved` and `r["handoff_note"]` ---
    # Phase 3: send the contact (and a deal for FORWARD / FORWARD_WITH_FLAG) to HubSpot
    # Phase 4: send FORWARD / FORWARD_WITH_FLAG leads to Telegram with a Claim button

    return {"ok": True, "call_id": call_id, "outcome": r["outcome"], "row_id": saved["id"]}
