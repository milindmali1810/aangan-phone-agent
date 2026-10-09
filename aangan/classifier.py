"""Qualification classifier.

Step 1 (AI): Gemini reads one enquiry and extracts facts + per-criterion judgements with quotes.
Step 2 (plain code): budget fit and the final outcome are decided here, so the rules are auditable.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config as C

ROOT = Path(__file__).resolve().parent.parent
RESULT = {"type": "STRING", "enum": ["pass", "fail", "unclear", "borderline"]}
CRITERION = {
    "type": "OBJECT",
    "properties": {"result": RESULT, "evidence": {"type": "STRING"}},
    "required": ["result", "evidence"],
}
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "caller_name": {"type": "STRING"},
        "phone": {"type": "STRING"},
        "locality": {"type": "STRING"},
        "scope_summary": {"type": "STRING"},
        "scope_kind": {"type": "STRING", "enum": ["full_home", "partial_home", "single_room", "office", "other", "not_given"]},
        "size_sqft": {"type": "NUMBER", "nullable": True},
        "designed_area_sqft": {"type": "NUMBER", "nullable": True},
        "timeline_text": {"type": "STRING"},
        "decision_maker_text": {"type": "STRING"},
        "budget_lakh_min": {"type": "NUMBER", "nullable": True},
        "budget_lakh_max": {"type": "NUMBER", "nullable": True},
        "budget_evidence": {"type": "STRING"},
        "site_status": {"type": "STRING"},
        "owner_or_tenant": {"type": "STRING"},
        "referral": {"type": "STRING"},
        "language": {"type": "STRING"},
        "asked_about_price": {"type": "BOOLEAN"},
        "is_complaint_or_existing_client": {"type": "BOOLEAN"},
        "is_unreachable": {"type": "BOOLEAN"},
        "real_project": CRITERION,
        "in_service_area": CRITERION,
        "timeline": CRITERION,
        "budget": CRITERION,
        "decision_maker": CRITERION,
    },
    "required": [
        "caller_name", "phone", "locality", "scope_summary", "scope_kind", "timeline_text",
        "decision_maker_text", "budget_evidence", "site_status", "owner_or_tenant", "referral",
        "language", "asked_about_price", "is_complaint_or_existing_client", "is_unreachable",
        "real_project", "in_service_area", "timeline", "budget", "decision_maker",
    ],
}


def _env_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found in .env")


def _prompt(transcript):
    t = (ROOT / "prompts" / "classify.md").read_text(encoding="utf-8")
    t = t.replace("{{services}}", (ROOT / "services.md").read_text(encoding="utf-8"))
    t = t.replace("{{qualified}}", (ROOT / "qualified.md").read_text(encoding="utf-8"))
    return t.replace("{{transcript}}", transcript)


def call_gemini(transcript):
    """Returns (extracted_dict, input_tokens, output_tokens)."""
    body = {
        "contents": [{"parts": [{"text": _prompt(transcript)}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{C.MODEL}:generateContent"
    for attempt in range(6):
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method="POST",
            headers={"x-goog-api-key": _env_key(), "Content-Type": "application/json"},
        )
        try:
            data = json.load(urllib.request.urlopen(req, timeout=90))
            usage = data.get("usageMetadata", {})
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text), usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 5:
                time.sleep(5 * (attempt + 1))  # rate limit or busy: wait and retry
                continue
            raise RuntimeError(f"Gemini HTTP {e.code}: {e.read()[:300].decode()}")


def budget_check(x):
    """Plain-code budget fit. Returns (result, note). result: pass | flag | fail."""
    hi = x.get("budget_lakh_max") or x.get("budget_lakh_min")
    if not hi:
        return "pass", "no budget volunteered"
    kind, area = x["scope_kind"], x.get("designed_area_sqft") or x.get("size_sqft")
    if kind in ("full_home", "office") and area:
        floor = C.HOME_FLOOR_PER_SQFT if kind == "full_home" else C.OFFICE_FLOOR_PER_SQFT
        rate = hi * 100000 / area
        ratio = rate / floor
        note = f"{hi:g} lakh over {area:g} sq ft is about {rate:,.0f} per sq ft ({ratio:.0%} of the {floor:,} floor)"
    elif kind in ("partial_home", "single_room"):
        ratio = hi / C.ROOM_FLOOR_LAKH
        note = f"{hi:g} lakh is {ratio:.0%} of the {C.ROOM_FLOOR_LAKH:g} lakh single-room floor"
    else:
        return "pass", "budget given but scope or area not clear enough to compare"
    if ratio < C.BUDGET_DECLINE_BELOW:
        return "fail", note
    if ratio < 1:
        return "flag", note
    return "pass", note


def decide(x):
    """Final outcome from the extracted facts. Returns (outcome, reason, flags)."""
    if x["is_complaint_or_existing_client"]:
        return "NEEDS_HUMAN", "Existing client or complaint: not a new lead; route to a human.", []
    if x["is_unreachable"]:
        return "NOT_CLASSIFIED", "Missed or unusable contact; call back.", []

    names = {"real_project": "Real project", "in_service_area": "Service area", "timeline": "Timeline"}
    fails = [f"{names[k]}: {x[k]['evidence'] or x[k]['result']}" for k in names if x[k]["result"] == "fail"]
    b_result, b_note = budget_check(x)
    if b_result == "fail":
        fails.append(f"Budget: {b_note}")
    if fails:
        return "DECLINE", "; ".join(fails), []

    flags = []
    for k, label in names.items():
        if x[k]["result"] == "unclear":
            flags.append(f"{label} not given or unclear: designer to establish")
    if x["timeline"]["result"] == "borderline":
        flags.append("Timeline is tight (6-10 weeks): confirm feasibility")
    if x["decision_maker"]["result"] == "unclear":
        flags.append("Decision-maker unclear: " + (x["decision_maker_text"] or "not given"))
    if b_result == "flag":
        flags.append("Budget below standard tier: designer to align expectations (" + b_note + ")")
    if flags:
        return "FORWARD_WITH_FLAG", "; ".join(flags), flags
    return "FORWARD", "Passes all five criteria.", []


def handoff_note(eid, x, outcome, flags):
    def g(v):
        return v if v not in (None, "", "not given") else "not given"
    budget = "not given"
    if x.get("budget_lakh_min") or x.get("budget_lakh_max"):
        lo, hi = x.get("budget_lakh_min"), x.get("budget_lakh_max")
        budget = f"{lo:g}-{hi:g} lakh (caller's own figure)" if lo and hi and lo != hi else f"{(hi or lo):g} lakh (caller's own figure)"
    size = f"{x['size_sqft']:g} sq ft" if x.get("size_sqft") else "size not given"
    lines = [
        f"Caller: {g(x['caller_name'])} | Phone: {g(x['phone'])}",
        f"Locality: {g(x['locality'])} | Type: {x['scope_kind']} | Site: {g(x['site_status'])} | {g(x['owner_or_tenant'])}",
        f"Scope: {g(x['scope_summary'])} ({size})",
        f"Needed by: {g(x['timeline_text'])}",
        f"Decides: {g(x['decision_maker_text'])}",
        f"Budget: {budget}",
        f"Referral: {g(x['referral'])}",
        f"Outcome: {outcome}" + (" | Flags: " + "; ".join(flags) if flags else ""),
        "Consultation slot: not booked",
        f"Transcript: enquiries/{eid}.txt",
    ]
    return "\n".join(lines)


def classify(eid):
    transcript = (ROOT / "enquiries" / f"{eid}.txt").read_text(encoding="utf-8")
    x, tin, tout = call_gemini(transcript)
    outcome, reason, flags = decide(x)
    cost = tin * C.PRICE_PER_M_INPUT_USD / 1e6 + tout * C.PRICE_PER_M_OUTPUT_USD / 1e6
    return {
        "id": eid, "outcome": outcome, "reason": reason, "flags": flags,
        "criteria": {k: x[k] for k in ("real_project", "in_service_area", "timeline", "budget", "decision_maker")},
        "budget_check": budget_check(x)[1],
        "extracted": {k: v for k, v in x.items() if k not in ("real_project", "in_service_area", "timeline", "budget", "decision_maker")},
        "handoff_note": handoff_note(eid, x, outcome, flags),
        "tokens_in": tin, "tokens_out": tout, "cost_usd_estimate": round(cost, 6), "model": C.MODEL,
    }
