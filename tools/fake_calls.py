"""Send FAKE Vaani events to a webhook address, to test the whole pipeline without spending Vaani credit.
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


def post_call(n, transcript, secs):
    room, cid = f"TEST-room-{n}", f"TEST-call-{n}"
    post({"event": "call_started", "room_name": room})
    time.sleep(1)
    return post({"event": "call_postprocessing", "call_id": cid, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                 "data": {"room_name": room, "call_id": cid, "call_duration": secs * 1000, "end_reason": "user_hangup",
                          "summary": "fake call", "entities": {}, "dispositions": {},
                          "recording_url": f"https://example.invalid/rec/{cid}.mp3", "transcript": transcript}})


print("wrong token  ->", post({"event": "x"}, token="wrong"))
print("good lead    ->", post_call(1, GOOD, 78))
print("same again   ->", post_call(1, GOOD, 78), "(re-delivery; must not duplicate)")
print("not a fit    ->", post_call(2, NOT_FIT, 25))
print("complaint    ->", post_call(3, COMPLAINT, 24))
print("empty call   ->", post_call(4, EMPTY, 6))
