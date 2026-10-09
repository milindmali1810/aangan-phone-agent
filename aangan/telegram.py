"""Telegram handoff: post a lead to the designers' group with a Claim button, record who claimed it and when,
and re-ping the group if nobody claims it.

Every lead is posted (Milind's decision). Leads someone must act on (FORWARD, FORWARD_WITH_FLAG, NEEDS_HUMAN) get a
Claim button and start the notified->claimed clock. DECLINE and NOT_CLASSIFIED are posted as quiet FYI messages,
to TELEGRAM_FYI_CHAT_ID if set (a separate group), otherwise to the main group.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from . import config as C
from . import db, env

IST = timezone(timedelta(hours=5, minutes=30))
CLAIMABLE = ("FORWARD", "FORWARD_WITH_FLAG", "NEEDS_HUMAN")
HEADER = {
    "FORWARD": "NEW LEAD",
    "FORWARD_WITH_FLAG": "NEW LEAD - CHECK THE FLAG",
    "NEEDS_HUMAN": "NEEDS A HUMAN - complaint or existing client",
    "DECLINE": "DECLINED - FYI, low priority",
    "NOT_CLASSIFIED": "CALL BACK - no usable conversation",
}


def enabled():
    return bool(env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID"))


def api(method, body):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{env.get('TELEGRAM_BOT_TOKEN')}/{method}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))["result"]
    except urllib.error.HTTPError as e:  # never include the URL in errors: it contains the bot token
        raise RuntimeError(f"Telegram {method} -> HTTP {e.code}: {e.read()[:200].decode()}")


def _answer(cq, **kw):
    """Acknowledge a button press. Telegram refuses this if the press is old; the claim itself is already saved."""
    try:
        api("answerCallbackQuery", {"callback_query_id": cq["id"], **kw})
    except RuntimeError:
        pass


def _claim_button(call_id):
    return {"inline_keyboard": [[{"text": "Claim this lead", "callback_data": f"claim:{call_id}"}]]}


def lead_text(outcome, note, reason=None):
    text = HEADER[outcome] + "\n\n" + (note or "(no details)")
    if outcome in ("DECLINE", "NEEDS_HUMAN", "NOT_CLASSIFIED") and reason:
        text += "\n\nWhy: " + reason
    return text


def send_lead(saved, row, result):
    """Post one saved call. Returns the Telegram message id."""
    outcome = row["outcome"]
    claimable = outcome in CLAIMABLE
    chat = env.get("TELEGRAM_CHAT_ID") if claimable else (env.get("TELEGRAM_FYI_CHAT_ID") or env.get("TELEGRAM_CHAT_ID"))
    body = {"chat_id": chat, "text": lead_text(outcome, row["handoff_note"], row["reason"])}
    if claimable:
        body["reply_markup"] = _claim_button(saved["id"])
    msg = api("sendMessage", body)
    patch = {"telegram_chat_id": str(chat), "telegram_message_id": msg["message_id"]}
    if claimable:
        patch["designer_notified_at"] = datetime.now(timezone.utc).isoformat()
    db.rest("PATCH", f"calls?id=eq.{saved['id']}", patch)
    return msg["message_id"]


def _person(user):
    name = " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p) or "someone"
    return name + (f" (@{user['username']})" if user.get("username") else "")


def handle_update(update):
    """Handles a button press. Only the first claim wins; anyone later is told who has it."""
    cq = update.get("callback_query")
    if not cq or not str(cq.get("data", "")).startswith("claim:"):
        return {"ignored": True}
    call_id = cq["data"].split(":", 1)[1]
    who = _person(cq["from"])
    now = datetime.now(timezone.utc)
    # the filter designer_claimed_at=is.null makes this atomic: two simultaneous clicks cannot both win
    won = db.rest("PATCH", f"calls?id=eq.{call_id}&designer_claimed_at=is.null",
                  {"designer_claimed_at": now.isoformat(), "designer_claimed_by": who},
                  "return=representation")
    if not won:
        row = db.rest("GET", f"calls?id=eq.{call_id}&select=designer_claimed_by") or [{}]
        _answer(cq, show_alert=True, text=f"Already claimed by {row[0].get('designer_claimed_by', 'someone else')}")
        return {"claimed": False}
    row = won[0]
    _answer(cq, text="It's yours. Please call the lead.")
    chat = row["telegram_chat_id"]
    for message_id in {row["telegram_message_id"], cq["message"]["message_id"]}:  # original + any reminder
        try:
            api("editMessageReplyMarkup", {"chat_id": chat, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
        except RuntimeError:
            pass
    api("sendMessage", {"chat_id": chat, "reply_to_message_id": row["telegram_message_id"],
                        "text": f"Claimed by {who} at {now.astimezone(IST).strftime('%I:%M %p')}."})
    return {"claimed": True, "by": who}


def reping():
    """Remind the group about leads nobody has claimed. Meant to be called every few minutes."""
    now = datetime.now(timezone.utc)
    cutoff = quote((now - timedelta(minutes=C.REPING_MINUTES)).isoformat())  # a raw "+" in a web address means a space
    rows = db.rest("GET", "calls?designer_claimed_at=is.null&designer_notified_at=not.is.null"
                          f"&designer_notified_at=lt.{cutoff}&reping_count=lt.{C.REPING_MAX}"
                          "&select=id,caller_name,locality,outcome,telegram_chat_id,telegram_message_id,"
                          "reping_count,last_reping_at,designer_notified_at")
    sent = 0
    for r in rows:
        if r["last_reping_at"] and datetime.fromisoformat(r["last_reping_at"].replace("Z", "+00:00")) >= now - timedelta(minutes=C.REPING_MINUTES):
            continue  # reminded recently enough
        waited = int((now - datetime.fromisoformat(r["designer_notified_at"].replace("Z", "+00:00"))).total_seconds() // 60)
        api("sendMessage", {
            "chat_id": r["telegram_chat_id"], "reply_to_message_id": r["telegram_message_id"],
            "text": f"Still unclaimed after {waited} minutes: {r['caller_name']}, {r['locality']}. Please claim it.",
            "reply_markup": _claim_button(r["id"])})
        db.rest("PATCH", f"calls?id=eq.{r['id']}", {"reping_count": r["reping_count"] + 1, "last_reping_at": now.isoformat()})
        sent += 1
    return {"checked": len(rows), "reminded": sent}
