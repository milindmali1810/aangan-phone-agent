"""Create (or find) the consultation schedule and event type in Cal.com. Safe to re-run: it reuses what it finds by name/slug.
Does not touch existing event types or schedules.   python tools/cal_setup.py"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import env

KEY = env.get("CAL_API_KEY")


def call(method, path, version, body=None):
    req = urllib.request.Request(
        "https://api.cal.com" + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + KEY, "cal-api-version": version, "Content-Type": "application/json",
                 "User-Agent": "aangan-phone-agent/1.0", "Accept": "application/json"})  # Cloudflare blocks the default Python agent
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read()[:500].decode()}")


SCHEDULE_NAME = "Aangan consultation hours"
sch = next((s for s in call("GET", "/v2/schedules", "2024-06-11")["data"] if s["name"] == SCHEDULE_NAME), None)
if not sch:
    sch = call("POST", "/v2/schedules", "2024-06-11", {
        "name": SCHEDULE_NAME, "timeZone": "Asia/Kolkata", "isDefault": False,
        "availability": [{"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                          "startTime": "10:00", "endTime": "19:00"}]})["data"]
    print("created schedule", sch["id"])
else:
    print("schedule already exists", sch["id"])

SLUG = "design-consultation"
et = next((e for e in call("GET", "/v2/event-types", "2024-06-14")["data"] if e["slug"] == SLUG), None)
if not et:
    et = call("POST", "/v2/event-types", "2024-06-14", {
        "title": "Design consultation", "slug": SLUG, "lengthInMinutes": 30, "scheduleId": sch["id"],
        "minimumBookingNotice": 1440,
        "description": "Free first consultation with an Aangan Studio interior designer. "
                       "Your designer will go through the scope, the site and the options with you."})["data"]
    print("created event type", et["id"])
else:
    print("event type already exists", et["id"])
print(json.dumps({"event_type_id": et["id"], "schedule_id": sch["id"], "slug": et["slug"], "minimumBookingNotice": et.get("minimumBookingNotice"),
                  "locations": et.get("locations"), "scheduleId": et.get("scheduleId")}, indent=1))
