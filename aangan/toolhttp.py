"""Shared plumbing for the two booking tools Vaani calls (/api/slots and /api/book).
Every call is recorded in the tool_log table (header NAMES only, never values), so when a tool call fails we can see exactly
what Vaani sent and what we answered."""
import hmac
import json
import sys
from urllib.parse import parse_qs, urlparse

from . import db, env


def _record(endpoint, h, key_ok, raw, status, answer):
    try:
        db.rest("POST", "tool_log", {
            "endpoint": endpoint, "http_method": h.command, "header_names": sorted(h.headers.keys()),
            "content_type": h.headers.get("Content-Type"), "key_ok": key_ok,
            "body": raw[:2000].decode("utf-8", "replace"), "status": status, "response": answer[:1500]})
    except Exception as e:  # logging must never break a booking
        print("tool_log error:", repr(e), file=sys.stderr)


def handle_tool(h, endpoint, fn):
    """h is the request handler. fn(data) returns the JSON answer for an authorised call."""
    secret = env.get("BOOKING_SECRET") or ""
    key_ok = bool(secret) and hmac.compare_digest(h.headers.get("X-Booking-Key", ""), secret)
    n = int(h.headers.get("Content-Length", 0) or 0)
    raw = h.rfile.read(n) if n else b""
    if not key_ok:
        status, body = 401, {"message": "not authorised"}
    else:
        try:
            try:
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    data = {}
            except ValueError:  # not JSON: maybe a form body
                data = {k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}
            data = {**{k: v[0] for k, v in parse_qs(urlparse(h.path).query).items()}, **data}
            status, body = 200, fn(data)
        except Exception as e:
            print(endpoint, "error:", repr(e), file=sys.stderr)
            status, body = 200, {"message": "The calendar could not be reached. Do not promise a time: say a designer will contact the caller to fix one."}
    answer = json.dumps(body, default=str)
    out = answer.encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(out)))
    h.end_headers()
    h.wfile.write(out)
    _record(endpoint, h, key_ok, raw, status, answer)
