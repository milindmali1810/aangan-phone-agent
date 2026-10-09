"""Telegram posts button presses here. Telegram sends our secret in a header, which we check."""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aangan import env, telegram  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass

    def do_GET(self):
        self._reply(200, {"ok": True, "service": "aangan telegram webhook"})

    def do_POST(self):
        secret = env.get("TELEGRAM_WEBHOOK_SECRET") or ""
        given = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secret or not hmac.compare_digest(given, secret):
            return self._reply(401, {"ok": False})
        try:
            update = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._reply(200, {"ok": True, **telegram.handle_update(update)})
        except Exception as e:  # always answer 200, or Telegram keeps retrying the same button press
            print("telegram webhook error:", repr(e), file=sys.stderr)
            self._reply(200, {"ok": False})
