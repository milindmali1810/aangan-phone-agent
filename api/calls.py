"""Call details for the dashboard, behind a password.
   GET /api/calls                 -> the latest calls (no transcripts)
   GET /api/calls?id=<call row id> -> one call in full: transcript, evidence for each criterion, handoff note, recording link
Header X-Dashboard-Key must equal DASHBOARD_PASSWORD. Totals on the dashboard stay public; names, phone numbers and
transcripts never leave this endpoint without the password."""
import hmac
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import db, env  # noqa: E402

LIST_FIELDS = ("id,vaani_call_id,source_id,channel,is_sample,call_started_at,outcome,reason,flags,caller_name,caller_phone,locality,"
               "property_type,size_sqft,consultation_booked,consultation_slot,designer_claimed_by,designer_claimed_at,"
               "voice_cost_usd,classification_cost_usd,call_seconds,recording_url")
_misses = {}  # very small brake on password guessing: after 8 wrong tries from one address, wait a minute


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        out = json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def _run(self):
        ip = (self.headers.get("x-forwarded-for") or "?").split(",")[0].strip()
        tries = [t for t in _misses.get(ip, []) if time.time() - t < 60]
        if len(tries) >= 8:
            return self._send(429, {"error": "too many wrong passwords, wait a minute"})
        secret = env.get("DASHBOARD_PASSWORD") or ""
        if not secret or not hmac.compare_digest(self.headers.get("X-Dashboard-Key", ""), secret):
            _misses[ip] = tries + [time.time()]
            return self._send(401, {"error": "wrong password"})
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        try:
            if q.get("id"):
                if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", q["id"]):
                    return self._send(400, {"error": "bad id"})
                rows = db.rest("GET", f"calls?id=eq.{q['id']}&select=*")
                return self._send(200, rows[0] if rows else {"error": "not found"})
            return self._send(200, {"calls": db.rest("GET", f"calls?select={LIST_FIELDS}&order=call_started_at.desc&limit=200")})
        except Exception as e:
            print("calls error:", repr(e), file=sys.stderr)
            return self._send(500, {"error": "could not read the calls"})

    do_GET = _run
