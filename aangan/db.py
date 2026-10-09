"""Tiny Supabase client (REST). Uses the SECRET key, so it only ever runs on our server."""
import json
import urllib.error
import urllib.request

from . import env


def rest(method, path, body=None, prefer=None):
    key = env.get("SUPABASE_SECRET_KEY")
    headers = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        env.get("SUPABASE_URL").rstrip("/") + "/rest/v1/" + path, method=method, headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
        return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Supabase {method} {path} -> HTTP {e.code}: {e.read()[:300].decode()}")
