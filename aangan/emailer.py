"""Email the team when a call books a consultation (Resend). Recipients: NOTIFY_EMAILS (comma separated).
Without a verified sending domain Resend only delivers to the account owner's own address, from onboarding@resend.dev;
add a domain in Resend later to email Nikhil and the designers too."""
import html
import json
import urllib.error
import urllib.request

from . import env

SENDER = "Aangan Leads <onboarding@resend.dev>"
DASHBOARD = "https://aangan-webhook.vercel.app/"


def enabled():
    return bool(env.get("RESEND_API_KEY") and env.get("NOTIFY_EMAILS"))


def _send(to, subject, text):
    req = urllib.request.Request(
        "https://api.resend.com/emails", method="POST",
        data=json.dumps({"from": SENDER, "to": to, "subject": subject, "text": text,
                         "html": "<div style=\"font:14px/1.55 system-ui,Segoe UI,sans-serif;color:#111\">" + html.escape(text).replace("\n", "<br>") + "</div>"}).encode(),
        headers={"Authorization": "Bearer " + env.get("RESEND_API_KEY"), "Content-Type": "application/json", "User-Agent": "aangan-phone-agent/1.0"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:  # never include the request (it carries the key) in the error
        raise RuntimeError(f"Resend HTTP {e.code}: {e.read()[:300].decode()}")


def send_booking(name, slot_text, handoff_note, outcome):
    """One email per booked consultation. Returns Resend's id."""
    to = [a.strip() for a in env.get("NOTIFY_EMAILS").split(",") if a.strip()]
    who = name if name and name != "not given" else "Unknown caller"
    flag = " (check the flag in the note)" if outcome == "FORWARD_WITH_FLAG" else ""
    text = (f"A consultation has been booked by the phone agent{flag}.\n\n"
            f"When: {slot_text}\nWho: {who}\n\n"
            f"--- What the designer needs ---\n{handoff_note or '(no details)'}\n\n"
            f"Full call, transcript and recording: {DASHBOARD} (password needed, section 'Calls')")
    return _send(to, f"Consultation booked: {who} - {slot_text}", text)["id"]
