"""Send FAKE Vaani events (in the shape Vaani's own test message showed) to a webhook address, to test the whole pipeline without spending Vaani credit.
   python tools/fake_calls.py http://localhost:8765/api/vaani_webhook      (local)
   python tools/fake_calls.py https://<site>/api/vaani_webhook             (deployed)
All fake calls use ids starting with TEST- so they can be found and deleted afterwards."""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aangan import env

BASE = sys.argv[1]
TOKEN = env.get("WEBHOOK_SECRET")

GOOD = """[00:01] AGENT: Hello, thank you for calling Aangan Studio. How can I help you today?
[00:05] USER: Hi, I'm Rahul Deshmukh. I have a three bedroom flat in Baner, about twelve hundred square feet. We want the whole home done, kitchen, wardrobes, everything.
[00:20] AGENT: Lovely. Is it already lived in, or are you getting possession soon?
[00:24] USER: We already live here, two years now. We want to start in January and finish by April.
[00:33] AGENT: Got it. Could I take your phone number?
[00:36] USER: Nine eight two two one one two two three three.
[00:44] AGENT: Nine eight two two, one one two two, three three. Is that right?
[00:48] USER: Yes. My wife and I decide together. And how much will it cost roughly?
[00:55] AGENT: Roughly eighteen hundred to thirty-five hundred rupees per square foot of carpet area. This is only an indicative range, not an exact price. Your designer will confirm the actual cost at the consultation.
[01:10] USER: Okay, that's fine. A friend, Sneha Kulkarni, referred me.
[01:18] AGENT: Thank you. A designer from our team will contact you to confirm a consultation time. Goodbye.
"""
NOT_FIT = """[00:01] AGENT: Hello, thank you for calling Aangan Studio. How can I help you today?
[00:05] USER: Hello, I am Mahesh Pawar from Nashik. I want to redo my office, about nine hundred square feet.
[00:16] AGENT: This sounds like it may not be the right fit for us right now, but feel free to reach out if your timeline or scope changes.
[00:22] USER: Okay, thank you.
"""
COMPLAINT = """[00:01] AGENT: Hello, thank you for calling Aangan Studio. How can I help you today?
[00:05] USER: My project has been going for three months and my designer has not replied in a week. This is not acceptable. I am Neeta Rao, flat in Viman Nagar.
[00:20] AGENT: I am passing this to our team right away.
"""
EMPTY = ""


def post(body, token=TOKEN):
    req = urllib.request.Request(f"{BASE}?token={token}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode()


def iso(offset_seconds=0):
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() + offset_seconds))


def events_for(n, transcript, secs, duration_value):
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    started = {"event": "call_started", "timestamp": iso(-secs),
               "data": {"call_id": cid, "room_name": room, "call_type": "Inbound",
                        "agent_name": "aangan-enquiry-agent", "phone_number": f"+9198000000{n:02d}"}}
    ended = {"event": "call_ended", "timestamp": iso(),
             "data": {"call_id": cid, "room_name": room, "end_reason": "completed", "call_duration": secs,
                      "technical_issue": False}}
    post = {"event": "call_postprocessing", "call_id": cid, "timestamp": iso(),
            "data": {"call_id": cid, "room_name": room, "call_duration": duration_value, "end_reason": "completed",
                     "summary": "fake call", "entities": {}, "dispositions": {},
                     "recording_url": f"https://example.invalid/rec/{cid}.mp3", "transcript": transcript}}
    return started, ended, post


# call 1: one BUNDLE of three events (duration in seconds)
s1, e1, p1 = events_for(1, GOOD, 78, 78)
print("wrong token     ->", post({"event": "x"}, token="wrong"))
print("vaani test msg  ->", post({"event": "webhook_test", "events": [s1, e1, p1], "timestamp": iso()}),
      "(must be logged only, no call created)")
print("1 good, bundle  ->", post({"events": [s1, e1, p1], "timestamp": iso()}))
print("1 again         ->", post({"events": [s1, e1, p1], "timestamp": iso()}), "(re-delivery; same row)")
# call 2: SEPARATE events, post-processing duration in seconds
for ev in events_for(2, NOT_FIT, 25, 25):
    r = post(ev)
print("2 not fit, single ->", r)
# call 3: post-processing duration in MILLISECONDS (24000 ms = 24 s); no call_ended duration known to it
a, b, c = events_for(3, COMPLAINT, 24, 24000)
for ev in (a, c):
    r = post(ev)
print("3 complaint, ms   ->", r)
# call 4: empty
for ev in events_for(4, EMPTY, 6, 6):
    r = post(ev)
print("4 empty           ->", r)
