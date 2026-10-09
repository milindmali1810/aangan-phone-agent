"""Called every few minutes by a timer. Reminds the group about unclaimed leads.  /api/reping?token=<WEBHOOK_SECRET>"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import pipeline, telegram  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _run(self):
        token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        if not pipeline.token_ok(token):
            code, body = 401, {"ok": False}
        else:
            try:
                code, body = 200, {"ok": True, **telegram.reping()}
            except Exception as e:
                print("reping error:", repr(e), file=sys.stderr)
                code, body = 500, {"ok": False}
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = _run
