"""Create or update the Aangan agent in Vaani from prompts/voice_agent.md.

  python tools/vaani_agent.py            create the agent (first time) or update it (if VAANI_AGENT_ID is in .env)
  python tools/vaani_agent.py --booking  same, with the in-call booking wording switched ON (only after linking Cal.com)
  python tools/vaani_agent.py --show     print the agent's current settings (nothing changed)

Needs VAANI_API_KEY in .env. Writes VAANI_AGENT_ID back to .env after creating.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
BASE = "https://api.vaanivoice.ai/api"
GREETING = "Hello, thank you for calling Aangan Studio. How can I help you today?"
MAX_CALL_MINUTES = 5  # protects the 100-rupee test credit


def env(name):
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return None


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": env("VAANI_API_KEY"), "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read()[:600].decode()}")


# Booking wording: OFF until Cal.com is linked in Vaani (otherwise the agent would claim bookings that never happen).
# Run with --booking once Cal.com is connected in Vaani's Settings -> Integrations.
booking = "booking_on.md" if "--booking" in sys.argv else "booking_off.md"
prompt = (ROOT / "prompts" / "voice_agent.md").read_text(encoding="utf-8").replace(
    "{{BOOKING}}", (ROOT / "prompts" / booking).read_text(encoding="utf-8").strip())
agent_id = env("VAANI_AGENT_ID")

if "--show" in sys.argv:
    print(json.dumps(call("GET", f"/agent/{agent_id}"), indent=2)[:4000])
    sys.exit()

if not agent_id:
    r = call("POST", "/create-agent", {"agent_display_name": "aangan-enquiry-agent",
                                       "config": {"persona": {"identity": {"system_prompt": prompt}}}})
    agent_id = r["agent_id"]
    with ENV.open("a", encoding="utf-8") as f:
        f.write(f"VAANI_AGENT_ID={agent_id}\n")
    print("Created agent", agent_id)

persona = call("PATCH", f"/agent/{agent_id}/persona", {
    "identity": {"system_prompt": prompt,
                 "greeting_message": {"agent_message": GREETING, "interruptible": True, "let_user_speak_first": False}},
    "senses_capabilities": {"language": "en", "auto_detect": True},
})
print("persona warnings:", persona.get("warnings"))

exp = call("PATCH", f"/agent/{agent_id}/experience", {
    "settings": {
        "call_settings": {"max_duration_enabled": True, "max_call_duration": MAX_CALL_MINUTES},
        "idle_conversation_settings": {"end_conversation_on_idle": True, "idle_call_warning_timeout": 10,
                                       "idle_call_hangup_timeout": 20},
    }
})
print("experience warnings:", exp.get("warnings"))
print("Done. Prompt length:", len(prompt), "characters. Max call:", MAX_CALL_MINUTES, "minutes.")
