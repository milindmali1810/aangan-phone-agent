"""Re-applies the correct descriptions and required fields to the two booking tools on the Vaani agent.
Vaani's "Paste cURL" helper auto-named the tools create_slot / create_booking, made every parameter required (email
included) and left the parameter descriptions empty. This puts that right. Safe to re-run. It keeps each tool's address
and header exactly as they are.   python tools/vaani_fix_tools.py"""
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


fs = copy.deepcopy(patch({})["persona"]["actions"]["functions"])
for f in fs:
    p = f["function_params"]["properties"]
    if f["function_name"] == "create_slot":
        f["description"] = ("Look up the free consultation times. This only checks the calendar and books nothing. Call it ONLY after the caller says yes to booking "
                            "a free consultation. Read out two or three of the times in the result. Never offer a time that is not in the result.")
        p["preferred_date"]["description"] = "The date the caller prefers, as YYYY-MM-DD, ONLY if they named a date. Otherwise leave this out."
        f["function_params"]["required"] = []
    if f["function_name"] == "create_booking":
        f["description"] = ("Book the consultation the caller chose. Call this only after the caller has confirmed the day and time aloud, and only after create_slot returned "
                            "that time. Use the exact start value from the create_slot result. Tell the caller it is booked only if this tool says it is booked.")
        p["start"]["description"] = "The exact start value of the chosen time, copied from the create_slot result (for example 2026-10-12T10:30:00+05:30)."
        p["name"]["description"] = "The caller's full name."
        p["phone"]["description"] = "The caller's phone number."
        p["email"]["description"] = "The caller's email address, ONLY if they gave one. Otherwise leave this out; do not ask for it again."
        f["function_params"]["required"] = ["start", "name", "phone"]
print("warnings:", patch({"actions": {"functions": fs}}).get("warnings"))
