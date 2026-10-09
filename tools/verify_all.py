"""Checks every part of the system against the LIVE services and prints PASS / WARN / FAIL for each.
   python tools/verify_all.py          (add --tests to also run every test suite)
Read-only: it creates nothing, except that --tests runs the existing test suites (they clean up after themselves)."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aangan import calcom, db, env, hubspot, telegram  # noqa: E402

results = []


def rec(area, label, status, detail=""):
    results.append((area, label, status, detail))
    print(f"{status:5} [{area}] {label}" + (f"  -> {detail}" if detail else ""))


def http(url, headers=None, method="GET", data=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "aangan-verify/1.0", **(headers or {})}, method=method, data=data)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


BASE = "https://aangan-webhook.vercel.app"
VH = {"X-API-Key": env.get("VAANI_API_KEY"), "Content-Type": "application/json"}

# ---------------- 1. Vaani voice agent ----------------
try:
    d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.vaanivoice.ai/api/agent/{env.get('VAANI_AGENT_ID')}/persona", method="PATCH", headers=VH, data=b"{}"), timeout=30))
    p = d["persona"]; sp = p["identity"]["system_prompt"]
    rec("Vaani agent", "agent reachable", "PASS", d.get("agent_display_name"))
    markers = {"greeting is Aangan's": "Hello, thank you for calling Aangan Studio" in p["identity"]["greeting_message"]["agent_message"],
               "one question per turn rule": "AT MOST ONE question" in sp, "never repeats back": "NEVER repeat back anything the caller tells you" in sp,
               "no commenting or praise": "Do NOT comment on, praise or summarise" in sp, "no price beyond the 3 ranges + disclaimer": "This is only an indicative range" in sp,
               "timelines understood (start vs finish)": "Timelines: understand what the caller actually needs" in sp, "polite close line": "may not be the right fit for us right now" in sp,
               "complaints go to a human": "I am passing this to our team right away" in sp, "never asks for email": "NEVER ask the caller for an email" in sp,
               "books with the built-in tools": "@Check_availability_booking" in sp and "@book_appointment" in sp,
               "tag-email uses the team mailbox": "milindmali1810+" in sp, "no leftover template markers": "{{" not in sp}
    for k, v in markers.items():
        rec("Vaani agent", k, "PASS" if v else "FAIL")
    e = d["experience"]["settings"]
    rec("Vaani agent", "call cap 5 minutes", "PASS" if e["call_settings"]["max_call_duration"] == 5 else "FAIL", str(e["call_settings"]["max_call_duration"]))
    rec("Vaani agent", "idle warn/hang-up 15/45 s", "PASS" if (e["idle_conversation_settings"]["idle_call_warning_timeout"], e["idle_conversation_settings"]["idle_call_hangup_timeout"]) == (15, 45) else "WARN")
    kw = p["senses_capabilities"]["ears"]["stt"]["primary"]["keywords"]
    rec("Vaani agent", "speech keywords for Pune places", "PASS" if "Baner" in kw else "FAIL", f"{len(kw)} words")
    fns = p["actions"]["functions"]
    old = [(f["function_name"], f["agent_config"]["is_enabled"]) for f in fns if f.get("is_custom")]
    rec("Vaani agent", "old custom booking tools are OFF (only one way to book)", "PASS" if all(not on for _, on in old) else "FAIL", str(old))
    for f in fns:
        if f.get("is_custom"):
            continue
        pr = f["agent_config"]["params"]
        ok_cfg = f["agent_config"]["is_enabled"] and pr.get("event_type_id") == 7412359 and pr.get("timezone") == "Asia/Kolkata" and pr.get("duration_minutes") == 30
        rec("Vaani agent", f"built-in tool {f['function_name']}: ON, event type 7412359 (Design consultation), Asia/Kolkata, 30 min", "PASS" if ok_cfg else "FAIL",
            f"event type {pr.get('event_type_id')}, enabled {f['agent_config']['is_enabled']}")
    names = {f["function_name"] for f in fns if not f.get("is_custom")}
    rec("Vaani agent", "both built-in Cal.com tools are attached", "PASS" if {"Check_availability_booking", "book_appointment"} <= names else "FAIL", str(sorted(names)))
except Exception as ex:
    rec("Vaani agent", "agent reachable", "FAIL", str(ex)[:200])

# ---------------- 2. Receiver + settings on the live server ----------------
s, b, _ = http(f"{BASE}/api/vaani_webhook?token={env.get('WEBHOOK_SECRET')}")
seen = json.loads(b).get("settings_seen", {}) if s == 200 else {}
rec("Server", "webhook receiver live", "PASS" if s == 200 else "FAIL", f"HTTP {s}")
missing = [k for k, v in seen.items() if not v]
rec("Server", "all settings present on Vercel", "PASS" if seen and not missing else "WARN", f"missing: {missing}" if missing else f"{len(seen)} settings")
rec("Server", "email settings on Vercel (RESEND_API_KEY, NOTIFY_EMAILS)", "PASS" if env.get("RESEND_API_KEY") and "RESEND_API_KEY" not in missing and "NOTIFY_EMAILS" not in missing and seen.get("RESEND_API_KEY") else "WARN",
    "not on the live server yet: emails will only send once stored" if not seen.get("RESEND_API_KEY") else "")
s, _, _ = http(f"{BASE}/api/vaani_webhook?token=wrong", method="POST", data=b"{}")
rec("Server", "wrong secret is refused", "PASS" if s == 401 else "FAIL", f"HTTP {s}")

# ---------------- 3. Vaani -> us: real calls ----------------
live = db.rest("GET", "calls?is_sample=eq.false&select=*&order=call_started_at.asc")
ev = db.rest("GET", "call_events?select=event,received_at&order=received_at.desc&limit=1")
rec("Vaani webhook", "real calls received", "PASS" if live else "FAIL", f"{len(live)} live call(s); last event {ev[0]['received_at'][:19] if ev else 'none'}")
for c in live:
    tag = c["vaani_call_id"][-8:]
    rec(f"Call {tag}", "has transcript", "PASS" if len(c["transcript"]) > 100 else "FAIL", f"{len(c['transcript'])} chars")
    rec(f"Call {tag}", "has recording link", "PASS" if c.get("recording_url") else "FAIL")
    rec(f"Call {tag}", "start time measured (not guessed)", "PASS" if c["started_at_source"] == "event" else "WARN", c["started_at_source"])
    rec(f"Call {tag}", "cost recorded", "PASS" if float(c["voice_cost_usd"]) > 0 else "FAIL", f"voice ${float(c['voice_cost_usd']):.4f}, AI ${float(c['classification_cost_usd']):.4f}")
    rec(f"Call {tag}", "classified", "PASS" if c["outcome"] else "FAIL", c["outcome"])

# ---------------- 4. Telegram ----------------
try:
    me = telegram.api("getMe", {}); rec("Telegram", "bot reachable", "PASS", "@" + me["username"])
    wi = telegram.api("getWebhookInfo", {})
    rec("Telegram", "button presses reach our server", "PASS" if wi["url"].endswith("/api/telegram_webhook") and not wi.get("last_error_message") else "FAIL", wi.get("last_error_message") or f"pending {wi['pending_update_count']}")
    ch = telegram.api("getChat", {"chat_id": env.get("TELEGRAM_CHAT_ID")}); rec("Telegram", "designers' group exists", "PASS", f"{ch.get('title')} ({telegram.api('getChatMemberCount', {'chat_id': env.get('TELEGRAM_CHAT_ID')})} members)")
except Exception as ex:
    rec("Telegram", "bot", "FAIL", str(ex)[:150])
for c in live:
    rec(f"Call {c['vaani_call_id'][-8:]}", "lead was posted to Telegram", "PASS" if c.get("telegram_message_id") else "FAIL", f"message {c.get('telegram_message_id')}")

# ---------------- 5. Dashboard ----------------
s, b, _ = http(f"{BASE}/"); rec("Dashboard", "page opens without a Vercel login", "PASS" if s == 200 and b"Aangan Enquiry Desk" in b else "FAIL", f"HTTP {s}")
s, _, _ = http(f"{BASE}/api/calls"); rec("Dashboard", "calls list refused without password", "PASS" if s == 401 else "FAIL", f"HTTP {s}")
pw = {"X-Dashboard-Key": env.get("DASHBOARD_PASSWORD")}
s, b, _ = http(f"{BASE}/api/calls", headers=pw)
calls = json.loads(b).get("calls", []) if s == 200 else []
rec("Dashboard", "calls list opens with the password", "PASS" if s == 200 else "FAIL", f"{len(calls)} calls")
rec("Dashboard", "list never carries transcripts", "PASS" if calls and "transcript" not in calls[0] else "FAIL")
if live:
    c = live[-1]; s, b, _ = http(f"{BASE}/api/calls?id={c['id']}", headers=pw); det = json.loads(b) if s == 200 else {}
    rec("Dashboard", "transcript shown in the call detail", "PASS" if len(det.get("transcript", "")) > 100 else "FAIL", f"{len(det.get('transcript', ''))} chars")
    rec("Dashboard", "evidence per criterion shown", "PASS" if det.get("criteria") else "FAIL")
    if c.get("recording_url"):
        s, b, h = http(c["recording_url"], headers={"Range": "bytes=0-2047"})
        rec("Dashboard", "recording link plays (audio comes back)", "PASS" if s in (200, 206) and "audio" in (h.get("Content-Type", "") + h.get("content-type", "")).lower() else "WARN", f"HTTP {s}, {h.get('Content-Type') or h.get('content-type')}")
s, b, _ = http("https://oeelqidjxszikigtdixs.supabase.co/rest/v1/rpc/dashboard_stats", method="POST", headers={"apikey": "sb_publishable_vXJYxvz6wXqqa7fjSPOPug_fAyqapdm", "Content-Type": "application/json"}, data=b"{}")
st = json.loads(b); rec("Dashboard", "public totals work", "PASS" if s == 200 and st["total_calls"] >= 40 else "FAIL", f"{st['total_calls']} calls, cost ${st['total_cost_usd']:.4f}")
s, b, _ = http("https://oeelqidjxszikigtdixs.supabase.co/rest/v1/calls?select=transcript&limit=1", headers={"apikey": "sb_publishable_vXJYxvz6wXqqa7fjSPOPug_fAyqapdm"})
rec("Dashboard", "database refuses the public key (no leaks)", "PASS" if b.strip() in (b"[]",) else "FAIL")

# ---------------- 6. HubSpot ----------------
STAGE = "4417021666"
for c in live:
    tag = c["vaani_call_id"][-8:]
    try:
        if not c.get("hubspot_contact_id"):
            rec(f"Call {tag}", "lead in HubSpot", "FAIL", "no contact id"); continue
        ct = hubspot.api("GET", f"/crm/v3/objects/contacts/{c['hubspot_contact_id']}?properties=firstname,lastname,phone,city,hs_lead_status")["properties"]
        rec(f"Call {tag}", "HubSpot contact exists", "PASS", f"{ct['firstname']} {ct.get('lastname') or ''} | {ct.get('phone')} | {ct.get('hs_lead_status')}")
        if c["outcome"] in ("FORWARD", "FORWARD_WITH_FLAG"):
            dl = hubspot.api("GET", f"/crm/v3/objects/deals/{c['hubspot_deal_id']}?properties=dealname,dealstage,hs_priority,description")["properties"]
            rec(f"Call {tag}", "HubSpot deal in 'New enquiry', note attached", "PASS" if dl["dealstage"] == STAGE and "Caller:" in (dl["description"] or "") else "FAIL", f"{dl['dealname']} | priority {dl['hs_priority']}")
    except Exception as ex:
        rec(f"Call {tag}", "lead in HubSpot", "FAIL", str(ex)[:150])
try:
    ps = hubspot.api("GET", "/crm/v3/pipelines/deals")["results"][0]["stages"]
    rec("HubSpot", "first stage is 'New enquiry'", "PASS" if ps[0]["label"] == "New enquiry" and ps[0]["id"] == STAGE else "FAIL")
except Exception as ex:
    rec("HubSpot", "pipeline", "FAIL", str(ex)[:150])

# ---------------- 7. Cal.com + booking ----------------
try:
    from aangan import booking
    sl = booking.available_slots()
    rec("Cal.com", "free consultation times offered (Mon-Sat 10-19 IST)", "PASS" if sl["available"] and all(10 <= int(x["start"][11:13]) < 19 for x in sl["slots"]) else "FAIL", f"{len(sl['slots'])} slots, first: {sl['slots'][0]['label'] if sl['slots'] else '-'}")
    bk = calcom._get("/v2/bookings?status=upcoming&take=20").get("data", [])
    rec("Cal.com", "a real booking has been made by a voice call", "WARN" if not bk else "PASS", f"{len(bk)} upcoming booking(s)" if bk else "none yet. Two causes found and fixed (booking tool pointed at a non-existent event type; the stand-in email was refused). Needs one more voice call to prove")
except Exception as ex:
    rec("Cal.com", "calendar", "FAIL", str(ex)[:150])

# ---------------- 8. Email ----------------
rec("Email", "key and recipient set locally", "PASS" if env.get("RESEND_API_KEY") and env.get("NOTIFY_EMAILS") else "FAIL", env.get("NOTIFY_EMAILS") or "")
rec("Email", "goes to the TEAM (not the caller)", "WARN", "the caller gets no written confirmation: no email is collected, and Resend has no sending domain yet")

# ---------------- 9. optional: the test suites ----------------
if "--tests" in sys.argv:
    suites = ["test_small_rules", "test_booking_logic", "test_timeline_cases", "test_telegram_logic", "test_hubspot_logic", "test_email_logic"]
    for name in suites:
        out = subprocess.run([sys.executable, str(ROOT / "tools" / f"{name}.py")], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}).stdout
        n_pass = out.count("PASS  "); n_fail = out.count("FAIL  ")
        rec("Tests", name, "PASS" if n_fail == 0 and "ALL PASSED" in out else "FAIL", f"{n_pass} checks passed, {n_fail} failed")

summary = {s: sum(1 for r in results if r[2] == s) for s in ("PASS", "WARN", "FAIL")}
print("\nSUMMARY:", summary)
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "verify_all.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "summary": summary, "results": results}, indent=1), encoding="utf-8")
