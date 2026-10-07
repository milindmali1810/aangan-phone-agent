# CLAUDE CODE PROMPT: Aangan Studio phone enquiry agent (Case 03)

Paste everything below this line into Claude Code, from the project folder that contains `services.md`, `qualified.md`, `pricing.md` and the `enquiries/` folder.

---

## 0. How we work together (read this first)

I am Milind, a PGP Startup Leadership student at Mesa School of Business. I have no coding background. I am not here to watch you build. I am here to build with you and to be able to explain every part of this to Nikhil, the founder.

Rules for the whole session:

1. **Explain before you execute.** Before writing code or running a command, tell me in plain English what it does and why. Translate any jargon immediately (for example: "a webhook is the other system knocking on our door when something happens").
2. **Small visible steps.** Never dump the whole solution. Show the thinking, then the step, then the result.
3. **When something breaks, teach.** Say what went wrong, why, and what to watch for next time, then fix it.
4. **Ask before assuming.** If something is ambiguous, ask me one targeted question. Do not guess and build in the wrong direction.
5. **Stop at the end of every phase.** Summarise what you built in one sentence I could say to a non-technical person, name the key decision, and ask me to explain it back in my own words before you continue. If I can't, re-explain a different way.
6. **Keep `BUILD_LOG.md`.** At the end of each phase and each session, append: what was built, what I learned, what broke and how it was fixed, what I can now do that I couldn't before, and the next step.
7. **Secrets:** put every key in a `.env` file, add `.env` to `.gitignore` before the first commit, and never print or commit a key. When I need a key, tell me exactly where to get it and what it allows the system to do.
8. Be direct and concise. Treat me as a smart person learning a new language, not a beginner who needs protecting from complexity.

## 1. The business case

Nikhil Deshpande runs Aangan Studio, an interior design studio in Pune (60 people, 14 designers). Enquiries arrive by phone, WhatsApp and a web form, about 200 a month. Facts from his own data:

- About 48% of enquiries get no response within 48 hours.
- An enquiry answered in under an hour converts at 4x the rate of one answered the next day.
- About a third arrive outside 10am-7pm. The front desk is two people.
- Average project value is ₹8-14 lakh.
- A forwarded enquiry reaches a designer with no context, so the designer's first call is spent re-asking what the front desk already asked.

His ask: every enquiry answered in five minutes, day or night. The ones worth a designer's time must reach the designer with everything already asked. He also wanted the system to quote per-square-foot pricing. **We are deliberately NOT building that (see section 3).**

**Scope of this build: incoming phone calls only.** WhatsApp and the web form are out of scope. Design the code so those channels could plug in later at the "receive an enquiry" step only, with everything after that reused. Do not build them.

## 2. The stack (from class)

| Tool | Job |
|---|---|
| Claude Code | where the project lives and is built |
| Vaani Labs | voice synthesis, telephony and call orchestration |
| Gemini Flash | classification and routing of a finished call (cheap, fast) |
| Cal.com (or Calendly / Google Calendar) | consultation booking inside the call |
| HubSpot | CRM: qualified calls become deals |
| Telegram | designer handoff (my choice, which I must defend: instant phone notification and a "Claim" button so two designers don't both call, or neither) |
| Supabase (or Neon) | call log, transcripts, cost log, state |
| Vercel | dashboard hosting |
| GitHub | saves progress between sessions |

Resend (email) is optional: only for a daily summary to Nikhil and as a fallback if Telegram fails. Build it last, if at all.

## 3. Hard rules for the voice agent (non-negotiable)

These come from `pricing.md` and `qualified.md`. Read both files, then build them in.

**The Cut: the agent never quotes a price.**
- Never say any number, range or per-square-foot figure. Never say "it'll cost around...", "our rates start at...", "for a 2BHK it's typically...".
- If a caller asks about pricing, the only acceptable reply is, verbatim: *"Pricing depends on the site, the materials you choose, and the scope — your designer will walk you through it in detail at the consultation. I can book that for you right now if you'd like."*
- `pricing.md` is loaded only as a guard so the agent knows what not to say. No number from it may appear in any output, prompt text spoken to a caller, handoff note, or dashboard. Asking for pricing never disqualifies a caller.

**Human only:** the agent never commits to anything (dates, scope, prices, discounts) beyond booking a consultation slot, and never handles complaints. For a complaint or anything outside enquiry intake: be polite, take their name and number, tag the record `needs-human` in the database and HubSpot, and send Nikhil a Telegram alert.

**Never guess.** Any field the caller didn't give is stored as `"not given"`. Never invent or infer a detail.

## 4. Qualification logic (build this first, with no external tools)

Source of truth: `qualified.md` (Nikhil's own rubric) and `services.md`. An enquiry is worth a designer's time when it passes five criteria:

1. **Real project, not just advice.** Wants design plus execution. Red flags: "just looking for ideas", "can you come and advise", "I'll do the execution myself". Minimum engagement is a room redesign with full execution.
2. **In service area.** Pune city or PCMC only. Use the locality list in `services.md` as a lookup. If a caller says "Pune" but the locality isn't on the list, ask which area. Decline Talegaon, Lonavala, Nashik, Mumbai and anywhere outside.
3. **Realistic timeline.** Ask "When would you need the project complete?"
4. **Right budget band, broadly.** Never quote, never probe. Only if the caller volunteers a number that is clearly far too low for the scope (for example ₹1-1.5 lakh for a full flat) address the mismatch on the call, and treat it as a fail. If budget is not mentioned, treat as pass.
5. **Decision-maker on the call or represented.** "My spouse wants this but isn't available" is fine if the caller confirms they are authorised. "Just doing initial research for my in-laws" is not enough on its own.

**What does NOT disqualify:** not knowing exactly what they want; calling outside office hours; asking for pricing; being unsure about materials, style or layout; a single room project with full execution; a rented apartment with no structural changes.

**Service scope check (from `services.md`):** no architecture or structural work, no decor or styling advice only, no standalone furniture sourcing, no Vastu-only consultation, no restaurants, hotels, retail or gyms. Commercial only up to about 3,000 sq ft.

### Three outcomes

- **FORWARD:** passes all five.
- **FORWARD_WITH_FLAG:** unclear on criterion 4 or 5 (never push on those on the call). Forward, and write the uncertainty into the handoff note.
- **DECLINE:** fails the rules below, with a one-line reason. The caller gets the graceful close: *"This sounds like it may not be the right fit for us right now — but feel free to reach out if your timeline or scope changes."*

On the call, if criterion 1, 2 or 3 is unclear, ask ONE direct question before deciding.

### Assumptions I am making (flagged, to confirm with Nikhil)

`qualified.md` contradicts itself: it says "if it fails one, close gracefully" and also "two or more criteria fail: decline". Also `qualified.md` says execution within 8-10 weeks while `services.md` says execution can't start under 6 weeks. Until Nikhil answers, implement these as clearly named settings in ONE config file so they are easy to change:

- **A1 (failures):** a hard fail on criterion 1, 2 or 3 declines on its own; a fail on criterion 4 (volunteered clearly-too-low budget) also declines; criterion 5 unclear forwards with a flag.
- **A2 (timeline):** needs it in under 6 weeks → decline. 6-10 weeks → forward with a flag. Longer → pass.

Tell me when you hit a case where these assumptions decide the outcome, so I can take real examples to Nikhil.

### Output format of the classifier

One structured result per call: `outcome`, a per-criterion result (`pass` / `fail` / `unclear`, each with the exact transcript words that justify it), a one-line `reason`, any `flags`, and the `handoff_note`. The one-line reason must be written so Nikhil can audit a decline later.

### Handoff note (what a designer receives)

Short and actionable, so the designer never re-asks the front desk's questions: caller name and number; locality; home or office; scope and size as stated; when they need it done; who decides; any budget the caller volunteered (or "not given"); outcome and flags (for example "budget unclear: designer to establish at consultation"); booked consultation slot if any; link to the full transcript.

## 5. Phases (stop and check in with me at the end of each)

### Phase 0: read, report, set up
- Read `services.md`, `qualified.md`, `pricing.md` and skim the `enquiries/` folder (40 anonymised transcripts across phone, WhatsApp and web form).
- Tell me in plain English what you understood: the business, the five criteria, the Cut, and what the transcripts look like. Tell me anything in the files that contradicts this prompt.
- Set up the project folder, `git init`, `.gitignore` (including `.env`), `BUILD_LOG.md`, and a GitHub repo with me.
- Explain what git and GitHub are doing for us in two sentences.

### Phase 1: qualification logic, tested before anything else
- Build the classifier (section 4) as a standalone function. Use Gemini Flash for the classification step. Explain why a cheaper model is enough when the rules are already written down. Ask me for the Gemini key and tell me what it allows.
- **Before you run it on the transcripts,** pick 10 of the 40 and have ME label each one (Forward / Forward with flag / Decline) using `qualified.md` and my own reading. Show me only the transcripts, not your answers. This is how I learn the rubric.
- Then run the classifier on all 40. Show a table: my label vs the classifier's, for the 10; the classifier's outcome and one-line reason for all 40.
- Count separately: **wrongly declined good leads** (the costliest error, because a lost project is ₹8-14 lakh) vs other mismatches. Walk me through each disagreement out loud and tell me whether the rule, the prompt or the transcript is at fault.
- Note which transcripts came from WhatsApp or the web form and may not look like live phone calls.
- Do not move on until I've explained the three outcomes and the "never guess" rule back to you.

### Phase 2: database and dashboard
- Supabase tables for calls and for cost. One row per call: caller details (nullable fields), full transcript, outcome, reason, flags, handoff note, `call_started_at`, `first_response_at`, `designer_notified_at`, `designer_claimed_at`, `consultation_booked` (yes/no, slot), voice cost, classification cost, call length, `needs_human`.
- Cost is a core requirement: the dashboard must show what the tool costs to run and what it generates, so Nikhil never has to pull numbers by hand again.
- Dashboard on Vercel, with: calls answered, average time to first response, % answered within 5 minutes and within 1 hour, outcomes (Forward / Flag / Decline), consultations booked, designer notified-to-claimed time, unclaimed leads, total cost, cost per call, cost per qualified lead. Baselines from the case for comparison: 48% unanswered in 48h; 4x conversion for under 1 hour.
- Explain every metric in plain English and why Nikhil cares. Seed it with the Phase 1 test results so it shows something before live calls exist.

### Phase 3: HubSpot
- Every caller becomes a HubSpot contact (declined callers too, with the decline reason, so Nikhil can audit the rules later). Forward and Forward-with-flag calls also become a deal, with the handoff note and a transcript link attached.
- Ask me for a HubSpot private app token and explain exactly which permissions it needs and why (least access). Prevent duplicate contacts when the same number calls twice.

### Phase 4: Telegram handoff
- Create the bot with me (BotFather) and a test group. Send only Forward and Forward-with-flag leads: handoff note, caller number, booked slot, transcript link, and a **Claim** button.
- Record who claimed it and when in the database (this feeds the dashboard). If unclaimed after 30 minutes, re-ping the group (this is my proposal to Nikhil, not his rule, so make the interval a setting). Explain the simplest reliable way to do the timer and the trade-offs.
- Be ready to defend Telegram vs email. Tell me the two biggest risks of Telegram (customer numbers sitting in a chat; designers who must actually join) and what we do about each.

### Phase 5: the voice agent (Vaani Labs)
- First, before building anything: read Vaani Labs' documentation and report to me what it supports: how to test a call (browser or test number) and whether an Indian number is possible, per-minute cost, how the live conversation is driven, how a finished call's transcript reaches our code, whether it can trigger a booking. If you can't access the docs, tell me exactly what to paste. Do not guess at Vaani's features. Wait for my go-ahead.
- Then build the agent's instructions from sections 3 and 4: friendly, short; asks name, number, locality, home or office, scope and size, when they need it done, who decides; one direct question where criterion 1, 2 or 3 is unclear; never pushes on budget or decision-maker; deflects pricing with the exact line; offers a consultation booking before ending.
- After each call: transcript → classifier → database → HubSpot → Telegram (if qualified) → cost row. Time-to-first-response must be recorded from the moment the call connects.
- Demo: a test call that I make myself, end to end.

### Phase 6: consultation booking inside the call
- Connect Cal.com (or Google Calendar) so the agent offers real open slots to Forward and Forward-with-flag callers and books one. Put the booked slot in the handoff note, HubSpot and the dashboard. Booking must never be offered to a Decline.

## 6. Definition of done for me

By the end I must be able to:
- Describe what we built in one sentence to a non-technical person.
- Explain the key decisions and defend them to Nikhil: why the Cut, why Telegram, why log declined callers, why a cheaper model classifies.
- Say what I'd change or add next, including how WhatsApp and the web form would plug in.
- Show Nikhil the dashboard and explain what each number costs and earns.
- Replicate the core logic myself with a new transcript.

## 7. First move

Start with Phase 0. Before you do anything, tell me in three sentences what you're about to do and why.
