# Aangan Studio: Lead Rubric (DRAFT v1, for Milind to review, then Nikhil to confirm)

Built from `services.md`, `qualified.md`, `pricing.md` and the 40 September transcripts.
Every number below comes from `pricing.md`, except the three settings marked **[PROPOSED]**, which are our suggestions for Nikhil to confirm. Nothing here is Nikhil's decision yet.

> Quoting is ON (section 5). The agent may speak only the ranges in section 5, always with the disclaimer. The tier tables in section 2 stay internal, for the classifier.

## 1. Scope gate: what Aangan can and cannot do

Checked first. Any "Out of scope" row means DECLINE (graceful close), whatever the budget.

| In scope | Out of scope |
|---|---|
| Apartment, villa or independent house, in Pune city or PCMC | Anything outside Pune / PCMC (Talegaon, Lonavala, Nashik, Mumbai...) |
| Full home (2BHK onwards), a full floor, or 2+ rooms, with execution | Advice, ideas, colour or furniture-arrangement only |
| Single room (bedroom or living room): complete redesign + execution | Decor or styling only; standalone furniture sourcing; Vastu-only |
| Office, clinic or studio up to about 3,000 sq ft | Restaurants, hotels, retail, gyms |
| Rented flat, if no structural change and landlord agrees | Architecture, moving walls, structural changes, permits |
| Site ready to start execution in 6+ weeks (A2 timeline rule) | Needs it finished in under 6 weeks |
| Existing-client complaints: not a lead, route to a human | |

Open point for Nikhil: commercial minimum size (T18 declined 180 sq ft citing 500 sq ft; no file says that).

## 2. Three buckets, based on budget fit against the price tiers

Same three outcomes as before. They are decided by scope gate first, then budget fit.

| Bucket | Meaning | Rule |
|---|---|---|
| **FORWARD** | Passes scope + budget fit (or budget not mentioned) + all other criteria | Designer notified, consultation offered |
| **FORWARD_WITH_FLAG** | In scope, but something is unclear or borderline | Designer notified with the specific doubt in the note |
| **DECLINE** | Out of scope, or budget clearly far below the floor | Graceful close, logged with a one-line reason |

### Routing: every lead goes to HubSpot AND the designer channel (Milind's decision)

The bucket does not stop a lead reaching a human. It only changes the label, the priority and what the caller is offered.

| Bucket | HubSpot | Designer (Telegram) | Caller is offered |
|---|---|---|---|
| FORWARD | Contact + deal | Normal priority, Claim button | Consultation booking |
| FORWARD_WITH_FLAG | Contact + deal, flag in note | Normal priority, doubt stated first | Consultation booking |
| DECLINE | Contact, decline reason attached | Labelled "DECLINED: low priority, FYI", reason shown | Graceful close, no booking |

Note: sending declines to designers costs attention. I suggest declines go to a separate quiet Telegram topic or thread so they don't bury real leads. To confirm with Nikhil.

### Budget fit (only when the caller volunteers a budget; never ask)

Implied rate = volunteered budget / carpet area of the space being designed.

**Residential tiers (per sq ft, carpet):** Standard 1,800-2,400 · Premium 2,400-3,500 · Luxury 3,500+
**Single-room floor:** 3.5 lakh (range 3.5-8 lakh)
**Commercial tiers (per sq ft):** Basic 1,200-1,800 · Mid 1,800-2,800 · Premium 2,800-4,000

| Implied rate vs lowest tier floor | Result |
|---|---|
| At or above the floor | Pass. Record the tier (Standard / Premium / Luxury, or Basic / Mid / Premium) in the note. |
| Between **[PROPOSED] 75%** and 100% of the floor | FORWARD_WITH_FLAG: "budget below standard tier, designer to align expectations" |
| Below **[PROPOSED] 75%** of the floor | DECLINE: "volunteered budget clearly far below scope" |
| No budget mentioned | Pass (per `qualified.md`) |
| Partial scope or single room | Compare total budget with the single-room floor (3.5 lakh) instead of per-sq-ft |

Worked examples from the transcripts (to test the rule, not to quote):

| Case | Budget / area | Implied rate | Result |
|---|---|---|---|
| T10 | 1-1.5 lakh, kitchen + bedroom | Below 3.5 lakh room floor | DECLINE |
| F10 | 18-22 lakh / 1,300 sq ft | about 1,400-1,700 | FLAG (between 75% and 100% of floor) |
| F03 | 15-20 lakh / 1,400 sq ft | about 1,070-1,430 | Borderline decline; also out of area, so DECLINE anyway |
| F06 | 35-40 lakh / about 1,950 sq ft (master excluded) | about 1,800-2,050 | Pass, Standard tier |
| F05 | 60-80 lakh / 2,200 sq ft commercial | about 2,700-3,600 | Pass, Mid to Premium tier |
| F08 | 4-5 lakh, 2 rooms | Above room floor, but 3-week timeline | DECLINE on timeline (A2) |

## 3. Extra rules for the designer segments (to confirm)

Proposed additions after reading the business. Each has a reason from the transcripts.

1. **Referral = priority.** Referred callers (T01, T05, W06, F09) are marked high priority in the Telegram note.
2. **Site status recorded:** possession done, bare shell, lived-in, or possession date. It decides the execution start date.
3. **Owner or tenant recorded.** Tenant needs landlord approval and no structural change (T11).
4. **Big-deal alert.** Residential over about 3,000 sq ft, or commercial over about 2,000 sq ft (T12, F05), also alerts Nikhil, not only the designer. **[PROPOSED]**
5. **Complaint / existing client / callback:** never classified as a lead. Tag `needs-human`, alert Nikhil (T09, T16).
6. **Structural work:** if the caller mentions moving walls, tag as out of scope.
7. **Unreachable lead:** dropped call or missed call gets a call-back task, logged as "not classified" (T08, T17).
8. **Language:** agent handles English and Hindi/Hinglish (W03).

## 4. Priority order the classifier follows

1. Complaint or existing client? Route to human, stop.
2. Scope gate (section 1). Any fail means DECLINE.
3. Timeline (A2: under 6 weeks DECLINE; 6-10 weeks FLAG).
4. Budget fit (section 2).
5. Decision-maker unclear? FLAG, never push.
6. Anything left: FORWARD.

## 5. Quoting: ON (Milind's decision, 2026-10-07)

`QUOTE_PRICE_RANGE = true`. When a caller asks about price, or once scope and area are known, the agent states the indicative range for their project type, then always adds the disclaimer. It never gives a single exact figure and never quotes anything not in the table below.

| Project type | Spoken range (from `pricing.md`) |
|---|---|
| Full or partial home | Standard to Premium: 1,800 to 3,500 per sq ft of carpet area; Luxury is higher |
| Single room redesign, all-in | 3.5 to 8 lakh |
| Office / clinic / studio | Basic to Premium: 1,200 to 4,000 per sq ft |

Required disclaimer, every time: "This is only an indicative range, not an exact price. Your designer will confirm the actual cost at the consultation, after seeing the site and the materials you choose."

**[PROPOSED]** The agent speaks the range per sq ft and does not multiply it by the caller's area, so it never says a total.

Risks to tell Nikhil: this goes against the "indicative only, no number to be quoted" note in `pricing.md`, so he must approve it. A caller may hold the studio to the number; a premium kitchen can cost 3x a standard one, so the range is wide on purpose.

Quoting never decides the bucket on its own. The bucket still comes from the budget the caller volunteers (section 2).
