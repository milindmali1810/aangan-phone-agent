# BUILD LOG: Aangan Studio phone enquiry agent

## Phase 0: read, report, set up (2026-10-07)

**What was built**
- Read `services.md`, `qualified.md`, `pricing.md` and all 40 transcripts (from `Aangan_Sep 2026_Enquiries.pdf`).
- Created the project folder structure: git repo, `.gitignore` (`.env` ignored before any commit), this log.

**What I learned**
- The five-criteria rubric, the Cut (never quote a price), and what the data looks like (20 phone, 10 WhatsApp, 10 web form).
- Source files contradict each other and the prompt in several places (see "Open questions for Nikhil").

**What broke and how it was fixed**
- The prompt expected an `enquiries/` folder; there is only one PDF. The PDF's text extracts with one word per line, so it needs cleaning before the classifier can use it. Fix planned for Phase 1.
- The PDF page-rendering tool (poppler) isn't installed; used Python `pypdf` for text instead.

**Open questions for Nikhil**
1. `qualified.md` says "if it fails one, close gracefully" AND "two or more criteria fail: decline". Which one?
2. `qualified.md` says site ready within 8-10 weeks; `services.md` says the hard minimum is 6 weeks. Which governs?
3. `services.md` says commercial up to ~3,000 sq ft; transcript T18 (180 sq ft pod) was declined for being "below 500 sq ft". No minimum is in either file.
4. Locality list covers some areas only (e.g. Kharadi, Nanded City, Sunderban/Aundh, Dahanukar Colony/Kothrud are not all listed by name).

**Next step:** Phase 1, the qualification classifier.

## Phase 1 (in progress, 2026-10-09)

- Wrote `tools/split_pdf.py`; it turns the PDF into 40 files in `enquiries/` (T01-T20 phone, W01-W10 WhatsApp, F01-F10 web form).
- Wrote `rubric.md`: scope gate, three buckets by budget fit against the price tiers, every lead to HubSpot and the designer channel, price quoting ON with a disclaimer (needs Nikhil's approval because `pricing.md` says do not quote).
- Created `label_these_10.md`: 10 shuffled enquiries for Milind to label BEFORE the classifier runs. The mapping from number to enquiry is kept out of git.
- Learned: the PDF's text has one word per line, so it must be flattened; section banners leaked onto the last enquiry of each section until they were cut.
- Next: Milind labels the 10, then we build the classifier (needs a Gemini key).

### Phase 1 result (2026-10-09)
- Built `aangan/classifier.py` (Gemini extracts facts + quotes; plain code applies the rules), `aangan/config.py` (all settings), `prompts/classify.md`, `run_batch.py`.
- Ran all 40. Cost about $0.07 for the 40 (about $0.0018 each, estimate). Outcomes: 15 Forward, 14 Forward with flag, 7 Decline, 3 Needs-human (complaints), 1 Not classified (missed call).
- vs my 10 reference labels: 9 of 10 match. 0 wrongly declined good leads. T02 differs (classifier flags the tight timeline).
- What broke: (1) gemini-2.5-flash was closed to new accounts (404), switched to gemini-3.8-flash. (2) "As soon as possible" was read as a deadline under 6 weeks and F04 was wrongly declined. (3) "Just exploring" was read as a clear timeline (W10). (4) W05 and W02 were marked unreachable although they had content. All three were prompt bugs; fixed in `prompts/classify.md`.
- Lesson: when a result looks wrong, read the evidence quote the model gave; it shows which instruction misled it.
- Open for Nikhil: how the 6-week rule is counted (T15, T02), minimum office size (T18), 75% budget line (F10), and what to do with "just exploring" leads (W10).

## Phase 2 (in progress, 2026-10-09)

**Built**
- Supabase project `aangan-phone-agent` (free plan, Mumbai). Tables `calls` and `cost_log`, locked by row-level security (no public reads or writes).
- One public function, `dashboard_stats()`, returns totals only (no names, numbers or transcripts). The dashboard page can call only this.
- `dashboard/index.html`: the dashboard. Deployed to Vercel as `aangan-dashboard` (protected by Vercel login by default).
- `tools/seed_supabase.py`: loads the 40 classified enquiries as sample rows. Waiting for the Supabase secret key in `.env`.

**Decisions**
- Dashboard shows totals only. Per-lead audit view needs a login; planned for later.
- `response_tracked` flag: web forms and complaints have no reply time in the data, so they are left out of speed numbers instead of counted as "unanswered".
- Sample rows are marked `is_sample` and the dashboard says so in a banner.

**What I learned**
- Anyone with the public key can call the database address, so the only safe design is: lock tables, expose one totals function.
- Vercel protects new sites with a login by default.

**Next:** Milind adds the Supabase secret key, seed runs, dashboard is checked against the classifier output.

### Phase 2 result (2026-10-09)
- Seeded 40 sample rows + 40 cost rows. Database counts match the classifier exactly (15 / 14 / 7 / 3 / 1). Total cost $0.0716 matches.
- Security check: with the public key, reading `calls` and `cost_log` returns nothing and inserting is refused. Only `dashboard_stats()` is open.
- Dashboard numbers on sample data: 40 enquiries; 17 of 27 tracked answered in 5 min (63%), 20 of 27 in 1 hour (74%), average 5.9 hours; cost $0.0018 per enquiry, $0.0025 per qualified lead.
- Caveat written into the banner: the sample only contains logged enquiries, so it flatters the front desk against Nikhil's 48% unanswered baseline.
- Still to do: the per-call view with recording + transcript (needs a login; the VaniBot brief says the dashboard must show them); redeploy with the new banner text.

### Notes from the VaniBot brief Milind pasted (for Phase 5)
- Testing is by WebRTC (browser simulated calls); no phone numbers. Each account has Rs 100 credit, voice costs about Rs 5-5.5 per minute, so about 15-18 minutes of testing in total. Test only once the whole application is built.
- Expected from a test call: Telegram message with lead details; qualified leads in HubSpot; every call (qualified or not) on the deployed dashboard with recording and transcript.
- The Actions integration (cal.com) is only needed if the agent books during the call.

## Phase 5 research (2026-10-09, while HubSpot token is pending)
- Found the Vaani developer docs (docs.vaanivoice.ai). Notes and open questions are in `docs/vaani-notes.md`. Nothing built yet; waiting for Milind's go-ahead as the brief requires.
- Learned: transcripts reach us by a `call_postprocessing` webhook; the docs do not describe webhook signing, retries, cost per minute, Indian numbers or inbound setup. Those need a real test or a question to Vaani.

### Phase 5 step 1: the Vaani agent (2026-10-09)
- Wrote `prompts/voice_agent.md` (the agent's instructions, from the rubric) and `tools/vaani_agent.py` (creates/updates the agent through Vaani's API). Created agent `aangan-enquiry-agent`; its id is saved as VAANI_AGENT_ID in `.env`.
- Settings applied and read back: prompt (5,740 chars), greeting, language auto-detect, default voice "devansh" (cartesia), max call length 5 minutes (protects the Rs 100 test credit), idle hang-up 20 s.
- Agent rules: collects name, number, locality, home/office, scope+size, timeline, decision-maker; one direct question if criterion 1-3 unclear; never probes budget; speaks only the three indicative ranges with the disclaimer (Milind's decision; Nikhil must approve because pricing.md says never quote); never multiplies a range into a total; cannot book yet, says a designer will confirm a time; graceful-close line verbatim; complaints go to a human.
- No call placed, no credit spent.
- Found: Vaani's OpenAPI file gives call details at `/api/call_details/{client}/{call_id}`, the docs page shows `/api/call_details/{call_id}`. Test which works before relying on either.
- Next: webhook receiver (needs a public URL on Vercel), register it in Vaani Settings -> Webhooks, then wire classifier -> database. HubSpot and Telegram plug in after.

### Phase 5 step 2: webhook receiver built and tested locally (2026-10-09)
- Built `aangan/pipeline.py` (what happens when Vaani reports a call), `api/vaani_webhook.py` (the public address; secret token in the URL), `aangan/env.py`, `aangan/db.py`, `tools/fake_calls.py` (fake-call tester), `vercel.json`. Standard library only, no installs.
- Database: new columns on `calls` (vaani_call_id, room, recording_url, summary, extra intake fields) and a `call_events` table. `vaani_call_id` is unique, so a call delivered twice is saved once.
- Classifier now also extracts: household notes, headcount, rooms wanted, contact preference, business description.
- Tested with FAKE calls, no Vaani credit: wrong secret refused (401); good lead -> FORWARD; Nashik office -> DECLINE; complaint -> NEEDS_HUMAN; empty call -> NOT_CLASSIFIED (no AI spend); re-delivery returned the same row; 2 cost rows per call; voice cost 78 s = Rs 7.15 at Rs 5.5/min. Test rows deleted afterwards (40 sample rows remain).
- What broke and how it was fixed:
  1. Regression: after my changes T02 flipped from Flag to Decline. Cause: the model was doing date arithmetic and applying the 6-week rule itself, inconsistently. Fix: the model now only reports `weeks_until_deadline`; the thresholds (under 6 = fail, 6-10 = borderline) are applied in code (`apply_timeline_rule`). 0 of 40 outcomes differ from the baseline now; T02 stable over 3 runs.
  2. Cost rows had mismatched fields (database refused them). Fixed.
  3. The old test server kept running with old code after I "restarted" it. Lesson: confirm the old process is really gone (check the port) before re-testing.
  4. The default server log printed the secret from the URL. Silenced.
  5. Handoff note pointed at a transcript file that doesn't exist for live calls. Now shows call id and recording link.
- Assumptions to confirm: Rs 5.5 a minute and 88 rupees to the dollar for voice cost; first response = call start (the agent greets the moment the call connects).
- Not done yet: deploying the receiver (needs the Gemini key, Supabase secret key and webhook secret stored on Vercel), registering the address in Vaani, HubSpot and Telegram steps.

### Phase 5 step 3: receiver deployed (2026-10-09)
- Created Vercel project `aangan-webhook`, connected to the GitHub repo (pushes to main redeploy it). Stored GEMINI_API_KEY, SUPABASE_SECRET_KEY, WEBHOOK_SECRET as sensitive settings and SUPABASE_URL as plain. Deployment READY at https://aangan-webhook.vercel.app/api/vaani_webhook
- Blocked: Vercel Authentication (default protection) redirects every request to a Vercel login (HTTP 302), so Vaani's webhook would never reach it. Needs Milind to switch protection off for this project; the endpoint is guarded by the secret token in the URL instead.
- Next: after that toggle, run `tools/fake_calls.py` against the deployed address, then register the address in Vaani (Settings -> Webhooks).

### Phase 5 step 3 result (2026-10-09)
- Milind turned Vercel protection off for `aangan-webhook`. The bare site address `/` shows 404 NOT_FOUND by design (only `/api/vaani_webhook` exists); the webhook address returns 200.
- Ran `tools/fake_calls.py` against https://aangan-webhook.vercel.app/api/vaani_webhook: same results as local (401 bad token; FORWARD; same row on re-delivery; DECLINE; NEEDS_HUMAN; NOT_CLASSIFIED). Call start was measured from call_started events across separate serverless runs. Test rows deleted; 40 sample rows remain.
- Next: Milind registers the address in Vaani (Settings -> Webhooks); one real WebRTC test call comes at the very end.

### Phase 5 step 3b: webhook registered in Vaani; real message shape learned (2026-10-09)
- Milind registered the address in Vaani (Developers -> Webhooks -> New End Point): name "Aangan pipeline", agent aangan-enquiry-agent, 5 events (call started, user picked up, call ended, call failed, call post-processing). Signing secret left empty (Vaani's docs do not explain how to verify it); our URL token is the check.
- Pressed Test Connectivity. It reached us and showed the REAL message shape, which differs from the docs:
  1. Vaani can send a BUNDLE: `{"event":"webhook_test","events":[...],"timestamp":...}`. Each inner event is `{"event","data":{call_id,room_name,...},"timestamp"}`.
  2. The sample shows `call_duration: 120` in both call_ended and call_postprocessing. The docs say seconds and milliseconds. Handled in code: call_ended is seconds; for post-processing, a value above 600 is milliseconds (our calls are capped at 300 seconds), otherwise seconds.
  3. Every event has its own timestamp (used as the measured call start) and call_started carries `phone_number` (used when the caller does not say their number).
  4. Transcript labels are "Agent:" / "User:".
- Rewrote `aangan/pipeline.py` for all of this; `webhook_test` messages are logged but never processed (their sample events would create a junk call).
- What broke: my "restarted" test server was an old copy still answering, because on Windows two programs can listen on one port. Fix: kill every listener and re-test on a fresh port, and check the response shape to know which code answered. Same lesson as before, now confirmed.
- Tested with fake calls in Vaani's real shapes: bundle -> 1 call; re-delivery -> same row; single events -> 1 call; ms duration -> 24 s; empty -> not classified; test message -> logged only.

## Phase 4: Telegram handoff (in progress, 2026-10-09)
- Built `aangan/telegram.py`, `api/telegram_webhook.py` (button presses; Telegram's secret header is checked), `api/reping.py` (reminder timer endpoint), and a hook in `pipeline.py` (a Telegram failure never loses a call). New columns on `calls`: telegram_chat_id, telegram_message_id, reping_count, last_reping_at. Settings in `aangan/config.py`: REPING_MINUTES = 30 (Milind's proposal), REPING_MAX = 6.
- Rules: every lead is posted. FORWARD / FORWARD_WITH_FLAG / NEEDS_HUMAN go to the main group with a Claim button and start the notified->claimed clock. DECLINE / NOT_CLASSIFIED go as quiet FYI messages (to TELEGRAM_FYI_CHAT_ID if set) with no button and no clock, so the dashboard's "unclaimed" number only counts leads someone must act on.
- `tools/test_telegram_logic.py`: 19 checks with a FAKE Telegram and the REAL database, all passing: routing, button, FYI for declines, first click wins, second told "Already claimed by X", 6 simultaneous clicks -> exactly 1 winner, reminders only for unclaimed leads, none twice within 30 minutes, again after 30.
- What broke: the reminder query put a timestamp with "+00:00" in a web address, where "+" means a space, so the database refused it. Fix: URL-encode it. Lesson: always encode values you put in a URL. One test failed because of my own test (same fake name in two calls), not the code.
- Waiting for: Milind's bot token (BotFather) and the group; then set the Telegram webhook, store the three Telegram settings on Vercel, add a timer for /api/reping, and do a real test in the group.

### Phase 4 step 2: real Telegram test (2026-10-09)
- Bot token verified (getMe): @aangan_leads1810_bot. Group "Milind and Aangan Leads" (private, 2 members: Milind + bot), chat id saved as TELEGRAM_CHAT_ID. Chose a GROUP, not a channel: designers can reply, and Telegram tells us exactly who pressed the button.
- Sent one real test lead through the real code path. Milind could not "claim" it: the Telegram -> our server connection (setWebhook) is not set yet, so presses wait in Telegram's queue. Both presses were queued. Processed them by hand with the real handler: first press claimed (designer_claimed_by Milind), second refused. Claim time was 10 minutes only because I processed it late.
- Made the claim robust: if Telegram refuses to acknowledge an old press, the claim is still saved and the button/reply are still sent.
- Test row deleted.
- Next: store the three Telegram settings on Vercel (needs Milind's OK, new keys), set Telegram's webhook to /api/telegram_webhook with a secret header, add the reminder timer, retest live.

### Phase 4 step 3: live and verified (2026-10-09)
- Stored TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, CRON_SECRET (sensitive) and TELEGRAM_CHAT_ID on the Vercel project aangan-webhook. Generated two new secrets: Telegram's header secret, and a CRON_SECRET used only by /api/reping, so the timer key can do nothing except trigger reminders.
- setWebhook points Telegram at /api/telegram_webhook (only callback_query updates, secret header checked; a wrong secret is refused).
- Reminder timer: Supabase pg_cron + pg_net, job `aangan-reping`, every minute, calls /api/reping. Verified: ran, got HTTP 200, "checked 0" with nothing due.
- Live test: sent a test lead, moved its notified time back 40 minutes; the timer found it within a minute and posted "Still unclaimed after 40 minutes"; Milind pressed Claim in Telegram and the claim (who + time) was recorded in the database through the live connection. Telegram webhook shows no errors. Test row deleted.
- Note: the pg_cron job text holds CRON_SECRET inside the database (visible only to database admins). Rotate it with the other secrets before go-live.
- Phase 4 left to consider: email fallback if Telegram fails (optional, last), and a separate quiet group for declines (set TELEGRAM_FYI_CHAT_ID).

## TO REVISIT LATER (Milind's request, 2026-10-09)
- **Phase 4 (Telegram): Milind wants to come back and optimise it.** Working today: lead post with Claim button, first-claim-wins, 30-minute reminders (max 6), declines as quiet FYI. Ideas on the table: separate quiet group for declines (TELEGRAM_FYI_CHAT_ID), reminder timing, message wording/length, email fallback if Telegram fails, privacy of customer numbers in the chat. REMIND MILIND at the end of each phase and before wrapping up.
- Rotate before go-live: Gemini key, Supabase secret key, Vaani key, webhook secret, Telegram bot token (BotFather /revoke), CRON_SECRET (also stored in the pg_cron job).

## Phase 3: HubSpot (built, 2026-10-09; real-API test waiting for a token)
- HubSpot account "Aangan Studio" (id 247643487) is connected to Claude through the HubSpot connector (works for Claude in a session only). It has HubSpot's two built-in sample contacts (left untouched) and the standard "Sales Pipeline" (7 stages, one pipeline on the free plan).
- Built `aangan/hubspot.py` + hook in `pipeline.py` (isolated: a CRM error never loses a call; the error is kept on the call row). Rules: every caller becomes a contact (declines too, with the reason in a note); FORWARD / FORWARD_WITH_FLAG also become a deal with the handoff note, priority High if referred; a repeat caller is found by phone (+91 normalised) and never duplicated, gets a "REPEAT CALLER" note, and a decline never overwrites an Open status; a call delivered twice makes nothing new (ids stored on the call row); no name and no phone = no junk contact. No price is ever put in HubSpot.
- New columns on `calls`: hubspot_contact_id, hubspot_deal_id, hubspot_error. Setting HUBSPOT_DEAL_STAGE in `aangan/config.py`.
- `tools/test_hubspot_logic.py`: 20 checks with a FAKE HubSpot and the REAL database, all passing.
- NOT yet verified against the real HubSpot API: the endpoint shapes and the standard association ids (note to contact 202, note to deal 214, deal to contact 3). Needs HUBSPOT_TOKEN (private app: contacts, deals, notes read/write only) on this computer and on Vercel.
- Open question for Milind: the free pipeline's first stage is called "Appointment Scheduled", which is misleading before a consultation is booked. Options: rename it to "New enquiry" (changes the CRM setup), or leave it.

### Phase 3 result: verified against the real HubSpot (2026-10-09)
- Milind created a HubSpot service key (HubSpot replaced private apps with service keys; Legacy apps are not available on this account) with four scopes: crm.objects.contacts.read/write and crm.objects.deals.read/write. The two notes scopes in my first list do not exist as separate scopes; HubSpot's docs say notes need only contacts.write. Saved as HUBSPOT_TOKEN in .env. NOT yet stored on Vercel.
- Renamed the first deal stage "Appointment Scheduled" -> "New enquiry" (Milind approved). HubSpot gave it a new id 4417021666; HUBSPOT_DEAL_STAGE updated. The other six stages are unchanged.
- `tools/test_hubspot_real.py` (4 fake calls, names start with TEST, phones +91900000000x): good lead -> contact (Open) + deal (High, New enquiry, linked to the contact) + notes on both; same phone calling again and declined -> no duplicate contact, status stayed Open, new note; new-phone decline -> Unqualified contact + reason note, no deal; re-delivery -> skipped. The association ids (note-to-contact 202, note-to-deal 214, deal-to-contact 3) are correct. Everything created was deleted afterwards; the CRM is back to its two built-in sample contacts.
- HubSpot behaviour to know: once a contact has a deal, HubSpot automatically moves their Lifecycle Stage from Lead to Opportunity.
- Next: store HUBSPOT_TOKEN on Vercel (needs Milind's OK) so live calls reach HubSpot.

### Live full-chain test (2026-10-09)
- Stored HUBSPOT_TOKEN on Vercel (sensitive). First live chain test: Telegram worked but HubSpot did not run. Cause: that deployment had not picked up the new setting even though it was created after it. Added a health check to the receiver (GET with the secret returns which settings the live server sees, yes/no only), redeployed, saw all nine settings true, re-ran: PASS.
- `tools/test_live_chain.py`: one fake call through https://aangan-webhook.vercel.app/api/vaani_webhook -> classifier -> database -> Telegram message (deleted afterwards) -> HubSpot contact + deal in "New enquiry" (deleted afterwards, with their notes). Database, HubSpot and Telegram all cleaned.
- Lesson: after adding a setting on Vercel, check the live server actually sees it (health check) before concluding anything.
- Everything after a call ends is now live: Vaani -> receiver -> classifier -> database -> Telegram + HubSpot -> dashboard totals.
- Remaining: Phase 6 booking (Cal.com), per-call dashboard page (login + recording + transcript), redeploy dashboard with new banner, one real WebRTC test call (Rs 100 credit), rotate secrets, Phase 4 optimisation (Milind's request), Nikhil questions list.

## Phase 6: Cal.com booking (built, 2026-10-09; needs two steps from Milind)
- Milind created a Cal.com account and an API key (CAL_API_KEY in .env, NOT yet on Vercel). Account: milind mali, Asia/Calcutta. Its built-in "15 min meeting" event and "Working hours" schedule were left untouched.
- `tools/cal_setup.py` created: schedule "Aangan consultation hours" (Mon-Sat 10:00-19:00, Asia/Kolkata) and event type "Design consultation" (30 min, 24 hours minimum notice = Claude's proposal; event type id 7412359). Verified the slots Cal.com would offer: Saturday only from 5 PM (24 h notice), no Sunday, Monday 10:00-18:30 in half hours.
- Lesson: Cal.com's front door (Cloudflare) blocks Python's default user agent with "error code 1010" (HTTP 403). Not a key problem. Send a User-Agent header.
- Voice prompt: booking wording is a switch. `{{BOOKING}}` in prompts/voice_agent.md is filled from prompts/booking_off.md (default: "a designer will contact you") or prompts/booking_on.md (offer 2-3 real slots, confirm aloud, book only for callers who fit, never for declines or complaints, ask email if the booking needs one, fall back to "a designer will contact you"). Applied OFF so far. Switch ON with `python tools/vaani_agent.py --booking` ONLY after Cal.com is linked in Vaani, otherwise the agent would claim bookings that never happen.
- `aangan/calcom.py` + hook in the pipeline: after a call that is FORWARD / FORWARD_WITH_FLAG, find the booking created while the call was in progress (match by time, since Vaani documents no link between a booking and a call). Fills consultation_booked/consultation_slot and the "Consultation slot" line of the handoff note (so Telegram and HubSpot show it). Never runs for declines. Failure never loses the call. Logic tested with fake bookings (old, cancelled, too-late ignored); a real read from Cal.com works. A real booking has NOT been tested; that happens in the real Vaani test call.
- Vaani's agent object has `integration_secrets: {}` and no documented way to set the Cal.com key through the API, so linking is a manual step in Vaani (Settings -> Integrations -> Cal.com).
- Open questions for the real call: does Vaani's booking need an email for a phone caller; does the agent check free slots first; what attendee details does Vaani put on the booking.
- Business point for Nikhil: a free Cal.com account is ONE calendar. 14 designers need team scheduling (paid) so consultations spread across designers.

### Phase 6 step 2: booking tools on our own server (2026-10-09)
- Milind connected the Cal.com key in Vaani (Integrations); it reaches the agent (integration_secrets), but Vaani has NO built-in Cal.com tool. Tools & Actions lists only system tools (hold, transfer, schedule callback, agent transfer, entity extraction); "New Action" -> "Create Custom Tool" is a generic HTTP tool (name, description, POST/GET + URL, timeout, headers, query params, parameters the agent extracts, and "store response fields as variables"). So booking goes through OUR server, which gives us control of slots, email and double-booking.
- Built `aangan/booking.py`, `api/slots.py` (POST, optional preferred_date) and `api/book.py` (POST: start, name, phone, optional email), protected by header X-Booking-Key = BOOKING_SECRET (in .env, NOT yet on Vercel). Slots: real free times only, up to 3 per day spread across the day, up to 4 days; a taken slot returns fresh times; Cal.com down never promises a time. A phone caller with no email gets a placeholder email `phone-<digits>@no-email.aangan.invalid` because Cal.com requires one (untested against real Cal.com: if it refuses the .invalid domain, switch NO_EMAIL_DOMAIN to example.com).
- `tools/test_booking_logic.py`: 15 checks (real Cal.com read-only for slots, fake Cal.com for booking), all passing.
- Still to do: store BOOKING_SECRET and CAL_API_KEY on Vercel (Milind's OK), deploy, create the two tools in Vaani (check_consultation_slots, book_consultation), switch booking wording ON (`python tools/vaani_agent.py --booking`, after updating prompts/booking_on.md with the tool names), one real test booking (sends Cal.com emails; ask first) and the real test call.

### Phase 6 step 3: tools attached to the agent (2026-10-09)
- Milind created the two tools with "Paste cURL". Vaani's helper AUTO-NAMED them: `create_slot` -> /api/slots and `create_booking` -> /api/book, wrote its own descriptions, made every parameter required (email included, preferred_date included) and left parameter descriptions empty. Milind switched both on for the agent (Persona -> Actions -> Custom Tools) and saved. Custom tools do not show in the agent record until attached; after attaching they appear under persona.actions.functions with their full definition (id, function_name, function_params, agent_config).
- Fixed through the API (`tools/vaani_fix_tools.py`, safe to re-run): create_slot description says it only looks up times and books nothing, preferred_date optional; create_booking required = start, name, phone (email optional and never insisted on), every parameter described (start = exact value from create_slot). Address and header untouched. Read back OK.
- Booking wording is ON in the agent prompt and uses the real tool names (SLOTS_TOOL / BOOK_TOOL constants in tools/vaani_agent.py). Saving from the Vaani page did NOT overwrite the prompt. Rule: after anything is changed in the Vaani page, refresh it before saving again, and re-run `python tools/vaani_agent.py --booking` to be safe.
- Vaani shows the agent estimate as Rs 5.60/min; config updated.
- NOT yet tested: an actual booking (chat test in Vaani's Chat tab, then cancel the booking in Cal.com). Needs Milind's "ok to book".
