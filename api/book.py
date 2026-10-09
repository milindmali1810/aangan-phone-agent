"""Vaani tool: book a consultation.  POST /api/book  with header X-Booking-Key.
Inputs: start (exact value from /api/slots), name, phone, email (optional)."""
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
                code, body = 200, booking.book(data.get("start"), data.get("name"), data.get("phone"), data.get("email"))
            except Exception as e:
                print("book error:", repr(e), file=sys.stderr)
                code, body = 200, {"booked": False, "message": "The booking did not go through. Do not promise a time: say a designer will contact the caller to fix one."}
        out = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_GET = do_POST = _run
