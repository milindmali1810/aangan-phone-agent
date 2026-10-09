"""Booking tools for the Vaani voice agent. The agent calls our server; our server talks to Cal.com.

check slots -> real free times only (Mon-Sat 10-19 India time, 24 h notice are enforced by Cal.com itself)
book        -> creates the booking; a phone caller with no email gets a placeholder address, so Cal.com accepts it.
"""
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

from . import config as C
from . import env
from .hubspot import normalize_phone

IST = timezone(timedelta(hours=5, minutes=30))
NO_EMAIL_DOMAIN = "no-email.aangan.invalid"  # placeholder; if Cal.com refuses it we switch to example.com (see BUILD_LOG)


def _cal(method, path, version, body=None):
    req = urllib.request.Request(
        "https://api.cal.com" + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + env.get("CAL_API_KEY"), "cal-api-version": version,
                 "Content-Type": "application/json", "User-Agent": "aangan-phone-agent/1.0", "Accept": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read()[:300].decode()}")


def _ts(v):
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(IST)


def spoken(dt):
    return dt.strftime("%A %d %B") + " at " + dt.strftime("%I:%M %p").lstrip("0")


def _pick(times):
    """Up to three times from a day, spread across the day (first, middle, last) so the caller has a real choice."""
    if len(times) <= 3:
        return times
    return [times[0], times[len(times) // 2], times[-1]]


def available_slots(preferred_date=None, max_days=4):
    """Free consultation times starting at preferred_date (YYYY-MM-DD) or today."""
    try:
        start = date.fromisoformat(str(preferred_date)[:10]) if preferred_date else datetime.now(IST).date()
    except ValueError:
        start = datetime.now(IST).date()
    start = max(start, datetime.now(IST).date())
    q = (f"/v2/slots?eventTypeId={C.CAL_EVENT_TYPE_ID}&start={start.isoformat()}"
         f"&end={(start + timedelta(days=10)).isoformat()}&timeZone=Asia/Kolkata")
    days = _cal("GET", q, "2024-09-04")["data"]
    slots, lines = [], []
    for day in sorted(days)[:max_days]:
        times = [_ts(s["start"]) for s in days[day]]
        if not times:
            continue
        chosen = _pick(times)
        lines.append(f"{chosen[0].strftime('%A %d %B')}: " + ", ".join(t.strftime("%I:%M %p").lstrip("0") for t in chosen))
        slots += [{"label": spoken(t), "start": t.isoformat()} for t in chosen]
    if not slots:
        return {"available": False, "message": "No free consultation times in the next ten days. Say that a designer will contact the caller to fix a time.", "slots": []}
    return {"available": True, "message": "Free consultation times (India time): " + "; ".join(lines) +
            ". Offer two or three of these only. When the caller picks one, call book_consultation with that slot's exact start value.",
            "slots": slots}


def book(start, name, phone, email=None):
    """Book one consultation. Returns a plain-language result the agent can speak."""
    name = (name or "").strip()
    if not start or not name:
        return {"booked": False, "message": "I still need the caller's name and the chosen time before booking."}
    try:
        when = _ts(start)
    except ValueError:
        return {"booked": False, "message": "The time was not understood. Use the exact start value from the list of free times."}
    phone_n = normalize_phone(phone)
    digits = re.sub(r"\D", "", phone_n or phone or "") or "unknown"
    email = (email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        email = f"phone-{digits}@{NO_EMAIL_DOMAIN}"
    attendee = {"name": name, "email": email, "timeZone": "Asia/Kolkata", "language": "en"}
    if phone_n:
        attendee["phoneNumber"] = phone_n
    try:
        res = _cal("POST", "/v2/bookings", "2024-08-13", {
            "start": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventTypeId": C.CAL_EVENT_TYPE_ID, "attendee": attendee,
            "metadata": {"source": "aangan-voice-agent", "phone": phone_n or "not given"}})["data"]
    except RuntimeError as e:
        if "no longer available" in str(e).lower() or "already" in str(e).lower() or "400" in str(e)[:4] or "409" in str(e)[:4]:
            alt = available_slots(when.date().isoformat())
            return {"booked": False, "message": "That time is no longer free. " + alt["message"], "slots": alt["slots"], "detail": str(e)[:200]}
        return {"booked": False, "message": "The booking did not go through. Do not promise a time: say a designer will contact the caller to fix one.", "detail": str(e)[:200]}
    return {"booked": True, "uid": res.get("uid"), "start": res.get("start"),
            "message": f"Booked: {spoken(when)} (India time). Confirm this day and time to the caller. A designer will meet them then."}
