"""Vaani tool: book a consultation.  POST /api/book  with header X-Booking-Key.
Inputs: start (exact value from /api/slots), name, phone, email (optional)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import booking, toolhttp  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _run(self):
        toolhttp.handle_tool(self, "book", lambda data: booking.book(data.get("start"), data.get("name"), data.get("phone"), data.get("email")))

    do_GET = do_POST = _run
