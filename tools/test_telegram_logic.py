"""Tests the Telegram rules with a FAKE Telegram (no network to Telegram) and the REAL database.
Creates TEST- rows and deletes them at the end.   python tools/test_telegram_logic.py"""
import os
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["TELEGRAM_BOT_TOKEN"] = "fake-token"
os.environ["TELEGRAM_CHAT_ID"] = "-100111"
os.environ["TELEGRAM_FYI_CHAT_ID"] = "-100222"

from aangan import db, pipeline, telegram  # noqa: E402

sent = []
_next_id = [1000]


def fake_api(method, body):
    sent.append((method, body))
    if method == "sendMessage":
        _next_id[0] += 1
        return {"message_id": _next_id[0]}
    return True


telegram.api = fake_api
src = open(Path(__file__).parent / "fake_calls.py", encoding="utf-8").read()
GOOD = src.split('GOOD = """')[1].split('"""')[0]
NOT_FIT = src.split('NOT_FIT = """')[1].split('"""')[0]


def now_iso(offset=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat()


def make_call(n, transcript, secs=60):
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    return pipeline.handle({"events": [
        {"event": "call_started", "timestamp": now_iso(-secs), "data": {"call_id": cid, "room_name": room}},
        {"event": "call_ended", "timestamp": now_iso(), "data": {"call_id": cid, "room_name": room, "call_duration": secs}},
        {"event": "call_postprocessing", "call_id": cid, "timestamp": now_iso(),
         "data": {"call_id": cid, "room_name": room, "call_duration": secs, "transcript": transcript,
                  "recording_url": "https://example.invalid/r.mp3"}}]})["processed"][0]


def click(call_id, user_id, first, msg_id):
    return telegram.handle_update({"callback_query": {
        "id": f"cb{user_id}", "data": f"claim:{call_id}", "from": {"id": user_id, "first_name": first},
        "message": {"message_id": msg_id}}})


def row(n):
    return db.rest("GET", f"calls?vaani_call_id=eq.TEST-call-{n}&select=*")[0]


ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + label)


try:
    # 1. a good lead is posted to the main group with a Claim button, and the clock starts
    sent.clear()
    r1 = make_call(1, GOOD)
    m = [b for k, b in sent if k == "sendMessage"][0]
    check("good lead goes to the main group", m["chat_id"] == "-100111")
    check("good lead has a Claim button", "reply_markup" in m and m["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("claim:"))
    check("message starts with NEW LEAD and carries the handoff note", m["text"].startswith("NEW LEAD") and "Rahul Deshmukh" in m["text"])
    check("transcript text is not in the message", "[00:01]" not in m["text"])
    d = row(1)
    check("designer_notified_at and message ids saved", d["designer_notified_at"] and d["telegram_message_id"] == r1["telegram_message"])

    tr = [b for k, b in sent if k == "sendMessage" and b.get("text", "").startswith("Transcript")]
    check("the transcript is sent as a reply under the lead", len(tr) == 1 and tr[0]["reply_to_message_id"] == r1["telegram_message"] and "AGENT:" in tr[0]["text"])
    long_t = "\n".join(f"[00:{i:02d}] USER: line number {i} " + "x" * 80 for i in range(120))
    sent.clear(); n = telegram.send_transcript("-100111", 5, long_t)
    check("a long transcript is split into several messages, none over 4,096 characters", n >= 3 and all(len(b["text"]) <= 4096 for k, b in sent) and "(1/" in sent[0][1]["text"])
    check("nothing is lost when splitting", "line number 119" in sent[-1][1]["text"] and "line number 0 " in sent[0][1]["text"])
    sent.clear()

    # 2. a decline is posted to the FYI group, with NO button and NO notified clock
    sent.clear()
    make_call(2, NOT_FIT)
    m = [b for k, b in sent if k == "sendMessage"][0]
    check("decline goes to the FYI group", m["chat_id"] == "-100222")
    check("decline has no Claim button", "reply_markup" not in m)
    check("decline starts with DECLINED and shows the reason", m["text"].startswith("DECLINED") and "Why:" in m["text"])
    check("decline does not start the claim clock", row(2)["designer_notified_at"] is None)

    # 3. first claim wins, second is refused
    sent.clear()
    a = click(row(1)["id"], 1, "Asha", r1["telegram_message"])
    b = click(row(1)["id"], 2, "Bharat", r1["telegram_message"])
    check("first person to click claims it", a == {"claimed": True, "by": "Asha"})
    check("second person is told it is taken", b == {"claimed": False})
    alerts = [x for k, x in sent if k == "answerCallbackQuery" and x.get("show_alert")]
    check("second person sees 'Already claimed by Asha'", alerts and "Asha" in alerts[0]["text"])
    d = row(1)
    check("claimer and time are recorded", d["designer_claimed_by"] == "Asha" and d["designer_claimed_at"])
    check("button removed after the claim", any(k == "editMessageReplyMarkup" and x["reply_markup"]["inline_keyboard"] == [] for k, x in sent))

    # 4. two people click at the same instant: exactly one wins
    make_call(3, GOOD)
    cid, mid = row(3)["id"], row(3)["telegram_message_id"]
    results = []
    ts = [threading.Thread(target=lambda i=i: results.append(click(cid, 10 + i, f"P{i}", mid))) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    check("6 simultaneous clicks: exactly one winner", sum(1 for r in results if r.get("claimed")) == 1)

    # 5. re-ping: only unclaimed, notified long enough ago, and not reminded recently
    make_call(4, GOOD)
    db.rest("PATCH", "calls?vaani_call_id=eq.TEST-call-4", {"designer_notified_at": now_iso(-40 * 60)})
    sent.clear()
    first = telegram.reping()
    check("40-minute-old unclaimed lead is reminded", first["reminded"] >= 1 and any("Still unclaimed after 40" in x.get("text", "") for k, x in sent))
    reminders = [x for k, x in sent if k == "sendMessage" and "Still unclaimed" in x.get("text", "")]
    check("claimed leads are never reminded (exactly 1 reminder: the unclaimed one)",
          len(reminders) == 1 and row(1)["reping_count"] == 0 and row(3)["reping_count"] == 0 and row(2)["reping_count"] == 0)
    sent.clear()
    second = telegram.reping()
    check("no second reminder straight away", second["reminded"] == 0 and row(4)["reping_count"] == 1)
    db.rest("PATCH", "calls?vaani_call_id=eq.TEST-call-4", {"last_reping_at": now_iso(-31 * 60)})
    sent.clear()
    third = telegram.reping()
    check("reminded again after another 30 minutes", third["reminded"] >= 1 and row(4)["reping_count"] == 2)
finally:
    db.rest("DELETE", "calls?vaani_call_id=like.TEST-*")
    db.rest("DELETE", "call_events?room_name=like.TEST-*")
    print("test rows deleted")
print("\nALL PASSED" if ok else "\nSOMETHING FAILED")
