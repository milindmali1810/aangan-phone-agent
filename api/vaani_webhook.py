"""Public address Vaani posts call events to:  https://<site>/api/vaani_webhook?token=<WEBHOOK_SECRET>
Vaani's docs do not describe request signing, so the secret in the address is our check."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import pipeline  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # the default log prints the address, which contains our secret
        pass

    def do_GET(self):  # lets you open the address in a browser to see that it is alive
        self._reply(200, {"ok": True, "service": "aangan vaani webhook"})

    def do_POST(self):
        token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        if not pipeline.token_ok(token):
            return self._reply(401, {"ok": False, "error": "bad token"})
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._reply(200, pipeline.handle(payload))
        except Exception as e:  # 500 so that Vaani can retry if it does retry
            print("webhook error:", repr(e), file=sys.stderr)
            self._reply(500, {"ok": False, "error": "processing failed"})
