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
