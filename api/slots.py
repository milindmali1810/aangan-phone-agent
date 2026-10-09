"""Vaani tool: free consultation times.  POST /api/slots  with header X-Booking-Key.  Optional input: preferred_date (YYYY-MM-DD)."""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import booking, env  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _run(self):
        secret = env.get("BOOKING_SECRET") or ""
        if not secret or not hmac.compare_digest(self.headers.get("X-Booking-Key", ""), secret):
            code, body = 401, {"message": "not authorised"}
        else:
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n) or b"{}") if n else {}
                data = {**{k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}, **data}
                code, body = 200, booking.available_slots(data.get("preferred_date"))
            except Exception as e:
                print("slots error:", repr(e), file=sys.stderr)
                code, body = 200, {"available": False, "message": "Could not check the calendar. Do not promise a time: say a designer will contact the caller to fix one.", "slots": []}
        out = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_GET = do_POST = _run
