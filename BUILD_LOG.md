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
