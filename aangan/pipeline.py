"""What happens when Vaani tells us about a call.

Vaani may send ONE event or a BUNDLE (`{"events": [...]}`); both are handled. Every event is logged in call_events.
call_postprocessing is the one that triggers work: classify the transcript, save the call + its costs.
HubSpot and Telegram steps plug in at the marked place once those phases are built.

Shapes below were taken from Vaani's own "Test Connectivity" message, not only from its docs.
"""
import hmac
from datetime import datetime, timedelta, timezone

from . import config as C
from . import db, env, telegram
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


def _clean(v):
    return "not given" if v in (None, "", "not given", "Not given") else v


def _seconds(value, from_call_ended):
    """Vaani's docs disagree with themselves about units (the test message shows 120 in both events).
    call_ended is documented as seconds. For call_postprocessing: our calls are capped at 5 minutes (300 s),
    so a number above 600 can only be milliseconds and anything at or below is seconds."""
    if value is None:
        return None
    return float(value) if from_call_ended or float(value) <= 600 else float(value) / 1000


def _event_rows(room, call_id):
    q = [f"vaani_call_id=eq.{call_id}"] if call_id else []
    if room:
        q = [f"room_name=eq.{room}"]
    return db.rest("GET", "call_events?" + "&".join(q) + "&order=received_at.asc&select=event,event_timestamp,received_at,payload") if q else []


def _timing(room, call_id, pp_ts, pp_duration):
    """Returns (started_at, how_we_know, duration_seconds, caller_phone)."""
    rows = _event_rows(room, call_id)
    started, how, dur, phone = None, "estimated", None, None
    for r in rows:
        ts = _parse_ts(r["event_timestamp"]) or _parse_ts(r["received_at"])
        data = (r["payload"] or {}).get("data") or {}
        phone = phone or data.get("phone_number")
        if r["event"] in START_EVENTS and started is None:
            started, how = ts, "event"
        if r["event"] == "call_ended" and data.get("call_duration") is not None:
            dur = _seconds(data["call_duration"], True)
    if dur is None:
        dur = _seconds(pp_duration, False)
    if started is None:
        end = pp_ts or datetime.now(timezone.utc)
        started = end - timedelta(seconds=dur or 0)
    return started, how, dur, phone


def _log(e, call_id, room):
    db.rest("POST", "call_events", {"room_name": room, "vaani_call_id": call_id, "event": e.get("event", "unknown"),
                                    "event_timestamp": e.get("timestamp"), "payload": e})


def handle(payload):
    if payload.get("event") == "webhook_test":  # Vaani's connectivity test: keep it, never process its sample events
        db.rest("POST", "call_events", {"event": "webhook_test", "payload": payload})
        return {"ok": True, "test": True}
    events = payload["events"] if isinstance(payload.get("events"), list) else [payload]
    results = []
    # log everything first, so start/end events are known before the postprocessing event is handled
    for e in events:
        d = e.get("data") if isinstance(e.get("data"), dict) else e
        _log(e, e.get("call_id") or d.get("call_id"), d.get("room_name"))
    for e in events:
        if e.get("event") == "call_postprocessing":
            results.append(_process_call(e))
    return {"ok": True, "events": len(events), "processed": results}


def _process_call(e):
    data = e.get("data") if isinstance(e.get("data"), dict) else e
    room, call_id = data.get("room_name"), e.get("call_id") or data.get("call_id")
    transcript = (data.get("transcript") or "").strip()
    started, source, dur, event_phone = _timing(room, call_id, _parse_ts(e.get("timestamp")), data.get("call_duration"))
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
    phone = _clean(x.get("phone"))
    if phone == "not given" and event_phone:  # the caller's number from the phone network beats nothing
        phone = event_phone
    voice_usd = ((dur or 0) / 60) * C.VOICE_RATE_INR_PER_MIN / C.INR_PER_USD
    row = {
        "vaani_call_id": call_id, "vaani_room_name": room, "channel": "phone", "is_sample": False,
        "caller_name": _clean(x.get("caller_name")), "caller_phone": phone,
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
        "call_seconds": round(dur) if dur else None,
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

    out = {"call_id": call_id, "outcome": r["outcome"], "row_id": saved["id"], "seconds": row["call_seconds"], "start": source}
    # Telegram: a failure here must never lose the call, which is already saved
    if telegram.enabled():
        try:
            out["telegram_message"] = telegram.send_lead(saved, row, r)
        except Exception as ex:
            out["telegram_error"] = str(ex)[:200]
            print("telegram error:", repr(ex)[:300])
    # --- Phase 3 plugs in here: send the contact (and a deal for FORWARD / FORWARD_WITH_FLAG) to HubSpot ---
    return out
