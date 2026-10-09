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
