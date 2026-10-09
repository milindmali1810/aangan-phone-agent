# Reference labels for the 10 test enquiries

Written by Claude on 2026-10-09, BEFORE any classifier was built or run. Milind waived labelling these himself.
Rules applied: `rubric.md` (A1 failures, A2 timeline, proposed 75% budget cut-off), `qualified.md`, `services.md`.

## Conventions I used (so labels are consistent)

1. **Criterion 5 (decision-maker):** passes when the caller speaks in the first person about their own home. It is "unclear" only when the caller signals someone else decides or that they are only researching.
2. **Missing information on criterion 1, 2 or 3:** the live agent would ask one question. In a finished transcript where that was never asked, the field is "not given" and the lead is FORWARD_WITH_FLAG, not guessed in either direction.
3. **Changed timeline:** the caller's last stated timeline is what counts.
4. **Not independent:** I wrote the rubric and these labels. They test that the classifier follows our reading of the rules, not that our reading matches Nikhil's. The judgement calls below must go to Nikhil.

| # in sheet | ID | Label | Deciding reason | Confidence |
|---|---|---|---|---|
| 1 | T15 | FORWARD | Undri (in area), full 2BHK with execution, owner with husband's approval, possession in about 6 weeks so execution starts after the 6-week minimum, no budget given | Medium: A2 ambiguity (see below) |
| 2 | F10 | FORWARD_WITH_FLAG | In area, real scope, decision-makers are the couple. Budget 18-22 lakh for 1,300 sq ft is about 1,385-1,690 per sq ft, between 75% and 100% of the 1,800 floor | Medium: depends on the proposed 75% line |
| 3 | T04 | DECLINE | Wants ideas on colours and arrangement only, "just exploring". Fails criterion 1 | High |
| 4 | T02 | FORWARD | Wakad, 950 sq ft full redesign, owner speaking, design from October. Price question is not a disqualifier | High |
| 5 | F03 | DECLINE | Talegaon Dabhade is explicitly out of area. Budget of 15-20 lakh for 1,400 sq ft is about 1,070-1,430 per sq ft, which straddles the 75% line (1,350), so it is not decisive. Fails criterion 2 | High |
| 6 | T18 | FORWARD_WITH_FLAG | 180 sq ft commercial pod. No file sets a minimum size. Location and timeline not given. Front desk declined for a "500 sq ft minimum" that exists in no rules file | Low: needs Nikhil |
| 7 | T10 | DECLINE | Volunteers 1-1.5 lakh for kitchen plus bedroom. Below the 3.5 lakh single-room floor, about 30-43% of it, under the 75% line. Fails criterion 4 | High |
| 8 | T14 | FORWARD_WITH_FLAG | Hadapsar (in area). Caller is the son, "initial checking", parents decide and will attend. Timeline not given. Criterion 5 unclear | High |
| 9 | T07 | FORWARD_WITH_FLAG | First ask (before Diwali, 3 weeks) is under 6 weeks, but the caller changed it to a start after Diwali, which is fine. Location, name and decision-maker not given. Caller has not committed | Medium: depends on convention 3 |
| 10 | T11 | FORWARD_WITH_FLAG | Baner, rented 2BHK with landlord OK and no structural change (allowed). Full design and fittings. Timeline never stated | Medium: convention 2 |

## Judgement calls to put to Nikhil

- **T15 / A2:** is the 6-week minimum measured from the call to the start of execution, or from the call to the finished project? I used start of execution.
- **T18:** is there a minimum commercial size? If 500 sq ft is a real rule, T18 becomes DECLINE.
- **F10 / the 75% line:** is a 1,400-1,700 per sq ft budget a flag or a decline?
- **T07 / convention 3:** should a lead that first asked for something impossible but then changed the date be forwarded?
