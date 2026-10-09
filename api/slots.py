"""Vaani tool: free consultation times.  POST /api/slots  with header X-Booking-Key.  Optional input: preferred_date (YYYY-MM-DD)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import booking, toolhttp  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _run(self):
        toolhttp.handle_tool(self, "slots", lambda data: booking.available_slots(data.get("preferred_date")))

    do_GET = do_POST = _run
