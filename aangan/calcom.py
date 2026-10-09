"""After a call: did the agent book a consultation in Cal.com while the caller was on the line?

Vaani's docs do not say how a booking is tied back to a call, so we match by TIME: the booking was created while the call
was in progress (or within a few minutes after it). Only the consultation event type is looked at.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone

from . import config as C
from . import env

IST = timezone(timedelta(hours=5, minutes=30))


def enabled():
    return bool(env.get("CAL_API_KEY"))


def _get(path):
    req = urllib.request.Request("https://api.cal.com" + path, headers={
        "Authorization": "Bearer " + env.get("CAL_API_KEY"), "cal-api-version": "2024-08-13",
        "User-Agent": "aangan-phone-agent/1.0", "Accept": "application/json"})  # Cloudflare blocks the default Python agent
    return json.load(urllib.request.urlopen(req, timeout=20))


def _ts(v):
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def pick(bookings, started, duration_seconds):
    """The booking made during the call (from 1 minute before it to 3 minutes after it ended), latest if several."""
    lo = started - timedelta(minutes=1)
    hi = started + timedelta(seconds=duration_seconds or 0) + timedelta(minutes=3)
    hits = [b for b in bookings if b.get("status") in ("accepted", "pending") and b.get("createdAt") and lo <= _ts(b["createdAt"]) <= hi]
    return max(hits, key=lambda b: b["createdAt"]) if hits else None


def pretty(b):
    return _ts(b["start"]).astimezone(IST).strftime("%a %d %b, %I:%M %p") + " IST"


def find_consultation(started, duration_seconds):
    """Returns the booking made during this call, or None."""
    data = _get(f"/v2/bookings?eventTypeId={C.CAL_EVENT_TYPE_ID}&status=upcoming&take=50")
    return pick(data.get("data", []), started, duration_seconds)
