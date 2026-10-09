"""Switch our two CUSTOM booking tools (create_slot, create_booking) on or off. The built-in Cal.com tools are never touched.
   python tools/vaani_tools_switch.py off      (both off)
   python tools/vaani_tools_switch.py on       (both on)
   python tools/vaani_tools_switch.py status"""
import copy
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import env

H = {"X-API-Key": env.get("VAANI_API_KEY"), "Content-Type": "application/json"}
URL = f"https://api.vaanivoice.ai/api/agent/{env.get('VAANI_AGENT_ID')}/persona"


def patch(body):
    return json.load(urllib.request.urlopen(urllib.request.Request(URL, method="PATCH", headers=H, data=json.dumps(body).encode()), timeout=30))


mode = sys.argv[1] if len(sys.argv) > 1 else "status"
fs = copy.deepcopy(patch({})["persona"]["actions"]["functions"])
if mode in ("on", "off"):
    for f in fs:
        if f.get("is_custom"):  # only OUR two custom tools; never touch the built-in Cal.com tools
            f["agent_config"]["is_enabled"] = (mode == "on")
    print("warnings:", patch({"actions": {"functions": fs}}).get("warnings"))
    fs = patch({})["persona"]["actions"]["functions"]
for f in fs:
    print(f["function_name"], "| custom:", bool(f.get("is_custom")), "| enabled:", f["agent_config"]["is_enabled"])
