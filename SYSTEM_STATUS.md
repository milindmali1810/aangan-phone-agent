# Aangan Studio phone enquiry agent: system status

**Checked live on 10 October 2026**, by `python tools/verify_all.py --tests` against the real services (Vaani, Vercel, Supabase, Telegram, HubSpot, Cal.com, Resend).

**Result: 63 live checks pass, 0 fail, 3 open items. All 79 checks in the 6 test suites pass.**

The honest summary: everything on your list works and is verified, **except one thing that is not yet proven**: a booking made *by a voice call* and the confirmation email that follows it. Two bugs that blocked it were found and fixed in this recheck. One more voice call proves it (see section 4).

---

## 1. Your checklist

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | **The voice AI agent** (what it says and does) | **Correct** | 12 instruction rules checked in the live agent (one question per turn, never repeats back, no praise or commentary, price only as three ranges with the disclaimer, firm-deadline logic, polite close, complaints to a human, never asks for an email, no leftover template text). Behaviour confirmed on 3 real voice calls. |
| 2 | **The Vaani agent** (its configuration) | **Correct** | Agent running; greeting set; 5-minute cap; idle prompt 15 s / hang-up 45 s; 34 Pune place names in speech recognition; both built-in Cal.com tools attached, ON, pointing at the Design consultation event type (7412359), Asia/Kolkata, 30 minutes; our old custom booking tools OFF. |
| 3 | **The Telegram bot** | **Correct** | Bot reachable, group exists, button presses reach our server with no errors, 3 real leads posted (messages 10, 11, 12), Claim button, first-claim-wins, 30-minute reminders (timer runs every minute). 22 test checks pass. |
| 4 | **The mail after a booking** | **Built and tested; not yet live** | A real sample email was delivered and opened. Trigger rules tested: sent only when a consultation is really booked, never for a decline. **Not yet switched on in the live server** (section 4). Goes to the **team** address, not the caller. |
| 5 | **Transcript in the dashboard and in Telegram** | **Correct** | Dashboard: transcript, evidence per criterion, recording (audio plays, `audio/ogg`) shown behind the password. Telegram: the transcript is sent as a reply under every lead (long ones split under 4,096 characters). Your 3 real calls were backfilled; every new call gets it automatically. |
| 6 | **Leads going to HubSpot** | **Correct** | All 3 real calls have a contact and a deal, in the **New enquiry** stage, with the handoff note. Calls 2 and 3 used the same phone number and **share one contact** (repeat caller recognised, not duplicated). No price is ever stored. |

---

## 2. What the 3 real voice calls showed

| Call | Length | Outcome | Notes |
|---|---|---|---|
| 1 | 67 s | Forward with flag | "Baner" heard as "Mani"; caller cut off by the idle prompt. Fixed (see section 3). |
| 2 | 159 s | Forward | Free times offered correctly. Agent asked for an email and speech recognition garbled it. Fixed. |
| 3 | 146 s | Forward | Natural flow, no email asked, slots offered, "10 in the morning" chosen, **but the booking did not complete.** Cause found and fixed. |

Costs are recorded per call (about Rs 6 to 15 for voice, under a cent for the AI).

---

## 3. Bugs found and fixed in this recheck

| Problem | Effect | Fix |
|---|---|---|
| `book_appointment` pointed at event type **7412344**, which does not exist in Cal.com (the right one is 7412359). | Booking could never work. | Corrected; read back from Vaani. |
| The stand-in email for callers without one (`example.com`) is **refused by Cal.com** ("cannot receive mail"). | Booking refused even with the right event type. | A tagged address of the team mailbox is used instead (`milindmali1810+<phone>@gmail.com`); tested against real Cal.com (accepted, then cancelled). Cal.com's confirmation therefore reaches the team inbox. |
| Vaani reported the booking tool as "success" although nothing was booked. | Looked fine in Vaani, wasn't. | Don't trust Vaani's tool status or its AI summary; trust Cal.com and our "Consultation slot" line. |
| **"Save Agent" in the Vaani page puts old settings back** (it re-enabled the old custom tools). | Two competing ways to book. | Switched off again. **Rule: refresh the page before touching it; avoid Save Agent.** |
| The agent praised and summarised what the caller said. | Repetition you did not want. | Explicit rule with examples added. |
| The "are you there?" prompt came after 10 s and hung up after 20 s. | A caller was cut off mid-thought. | 15 s and 45 s. |
| Transcript was not in Telegram. | Missing from your list. | Added as a reply under each lead. |
| Three settings existed but nothing used them (office size limit, big-project marker). | Silent gaps. | Wired in and tested. |
| Chat test panel cannot run tools (any tool errors there). | Hours lost testing booking in chat. | Test booking **by voice only**. |

---

## 4. Not yet proven, and what closes each

| Open item | What it needs |
|---|---|
| **A booking made by a voice call.** Both blockers are fixed, but no call has run since. | One voice call (about Rs 12 to 17): say yes, pick a time. I then check Cal.com and cancel the test booking. |
| **Email on the live server.** `RESEND_API_KEY` and `NOTIFY_EMAILS` are only on this computer. | Your OK to store the two settings on Vercel (hidden), then redeploy. |
| **Email to the caller.** The agent deliberately does not ask for an email (spoken emails are misheard), and Resend has no sending domain, so nobody but you can be emailed yet. | Decide: WhatsApp or SMS confirmation to the caller, and/or a verified domain so Nikhil and the designers get the email too. |

---

## 5. Test data currently in the live systems

- **Database:** 40 September sample rows (marked as samples) and 3 real test calls ("Asha").
- **HubSpot:** 2 contacts and 3 deals from those test calls, plus HubSpot's 2 built-in sample contacts.
- **Telegram group:** 3 test leads with their transcripts.
- **Cal.com:** no bookings (test bookings were cancelled).

Delete before real use: say the word and I remove the test contacts, deals and rows.

---

## 6. Still needed before real customers

1. Nikhil confirms the proposed rules (13 open questions in `Aangan_Phone_Agent_Parameters.pdf`, last page), including that the agent may speak price ranges.
2. **Rotate every key** that was pasted in chat: Gemini, Supabase, Vaani, HubSpot, Cal.com, Telegram bot, Resend, and the webhook, booking, cron and dashboard secrets.
3. Your Telegram optimisation (kept open at your request).
4. A real Indian phone number: Vaani's docs do not confirm one can be provisioned; the tests so far are browser calls.
5. A free Cal.com account is **one calendar**; 14 designers need team scheduling.

---

## 7. How to re-check at any time

```
python tools/verify_all.py            # live checks, read-only
python tools/verify_all.py --tests    # also runs all 6 test suites
```

Other files: `BUILD_LOG.md` (what was built, what broke, what was learned), `rubric.md` (the rules), `Aangan_Phone_Agent_Parameters.pdf` (every parameter), `docs/vaani-notes.md`.
Live dashboard: https://aangan-webhook.vercel.app/ (password needed under "Calls").
