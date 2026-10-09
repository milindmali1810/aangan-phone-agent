"""Builds Aangan_Phone_Agent_Parameters.pdf: every parameter of the system, where it lives, and who must confirm it.
Contains NO keys or secrets.   python tools/make_parameters_pdf.py"""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "Aangan_Phone_Agent_Parameters.pdf"
INK, MUTED, LINE = colors.HexColor("#1b1b1a"), colors.HexColor("#6b6a66"), colors.HexColor("#d9d8d2")
HEAD, ACCENT = colors.HexColor("#1f3a5f"), colors.HexColor("#2a78d6")
CONF, PROP, TEST = colors.HexColor("#0a7a0a"), colors.HexColor("#b25b00"), colors.HexColor("#8a2be2")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.2, leading=12.6, textColor=INK)
small = ParagraphStyle("small", parent=body, fontSize=8.2, leading=10.8)
cellb = ParagraphStyle("cellb", parent=small, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=HEAD, spaceBefore=14, spaceAfter=5)
h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=ACCENT, spaceBefore=8, spaceAfter=3)
title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=HEAD)
sub = ParagraphStyle("sub", parent=body, fontSize=11, leading=15, textColor=MUTED)
note = ParagraphStyle("note", parent=small, textColor=MUTED, spaceBefore=3)

STATUS = {"C": ("Nikhil's rule", CONF), "P": ("PROPOSED: Nikhil to confirm", PROP), "B": ("Built and tested", TEST)}


def P(t, st=small):
    return Paragraph(t, st)


def tag(code):
    label, col = STATUS[code]
    return Paragraph(f'<font color="{col.hexval()}"><b>{label}</b></font>', small)


def table(rows, widths, header=True, status_col=None):
    data = []
    for r_i, r in enumerate(rows):
        row = []
        for c_i, cell in enumerate(r):
            if header and r_i == 0:
                row.append(Paragraph(f'<font color="white"><b>{cell}</b></font>', small))
            elif status_col is not None and c_i == status_col and cell in STATUS:
                row.append(tag(cell))
            else:
                row.append(P(cell, cellb if c_i == 0 else small))
        data.append(row)
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), HEAD))
        st += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f6f3")) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(st))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "Aangan Studio phone enquiry agent - system parameters")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


S = []
S += [Spacer(1, 30 * mm), Paragraph("Aangan Studio", sub), Paragraph("Phone Enquiry Agent: all parameters", title), Spacer(1, 4 * mm),
      Paragraph(f"Every rule, number and setting the system runs on, where it lives, and who has to confirm it. Version of {date.today().strftime('%d %B %Y')}.", sub),
      Spacer(1, 8 * mm)]
legend = [["Tag in the last column", "What it means"],
          ["Nikhil's rule", "Taken from Nikhil's own files (services.md, qualified.md, pricing.md). Not our invention."],
          ["PROPOSED: Nikhil to confirm", "A number or rule WE proposed because his files were silent or contradicted each other. Needs his sign-off before go-live."],
          ["Built and tested", "How the system works. Not a business rule, so it needs no sign-off."]]
lt = Table([[Paragraph(f"<b>{a}</b>" if i else f'<font color="white"><b>{a}</b></font>', small), Paragraph(b if i else f'<font color="white"><b>{b}</b></font>', small)] for i, (a, b) in enumerate(legend)],
           colWidths=[48 * mm, 122 * mm])
lt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), HEAD), ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TEXTCOLOR", (0, 2), (0, 2), PROP), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
S += [lt, Spacer(1, 6 * mm),
      P("<b>How a call flows.</b> The caller phones. The Vaani voice agent talks to them. When the call ends, Vaani sends the call to our server. "
        "An AI model (Gemini Flash) reads the transcript and pulls out facts with quotes; plain code then applies the rules below and decides the outcome. "
        "The call is saved to the database with its cost, posted to the designers' Telegram group, and sent to HubSpot. The dashboard shows the totals.", body),
      Spacer(1, 3 * mm), P("<b>No secrets are in this document.</b> Keys and tokens live only in the private .env file and in Vercel's hidden settings.", body), PageBreak()]

# 1 outcomes
S += [Paragraph("1. The five outcomes", h1),
      table([["Outcome", "Meaning", "What happens next"],
             ["FORWARD", "Passes all five criteria.", "Telegram post with a Claim button; HubSpot contact and deal; caller offered a consultation."],
             ["FORWARD_WITH_FLAG", "Fits, but one thing is unclear or borderline (budget a little low, tight timeline, someone else decides, details missing).", "Same as Forward, with the doubt written at the top of the note for the designer."],
             ["DECLINE", "Out of scope, or a firm problem (outside Pune and PCMC, advice only, firm finish date under 6 weeks, budget far too low, office over 3,000 sq ft).", "Polite close, no booking offered. Logged in HubSpot with the reason; quiet 'FYI' post in Telegram, no Claim button."],
             ["NEEDS_HUMAN", "An existing client with a complaint or a chaser.", "Not treated as a lead. Posted with a Claim button; HubSpot note; someone senior calls back."],
             ["NOT_CLASSIFIED", "A missed or empty call with nothing usable.", "Logged for a call-back. No AI cost."]],
            [34, 70, 66])]

# 2 criteria
S += [Paragraph("2. The five qualification criteria", h1),
      table([["Criterion", "The rule", "Status"],
             ["1. Real project", "Wants design AND execution. Minimum is a complete room redesign with execution. Fails for: advice or ideas only, decor or styling only, furniture sourcing only, Vastu only, structural or architecture work, restaurants, hotels, shops, gyms.", "C"],
             ["2. In service area", "Pune city or PCMC only. Named areas include Kothrud, Baner, Aundh, Wakad, Koregaon Park, Kalyani Nagar, Viman Nagar, Hadapsar, Magarpatta, NIBM, Kondhwa, Undri, Shivane, Warje, Erandwane, Deccan, Pimpri, Chinchwad, Pimple Saudagar, Pimple Nilakh, Ravet, Hinjewadi and adjoining areas. If only 'Pune' is said, ask which area. Declined: Talegaon, Lonavala, Nashik, Mumbai, any other city.", "C"],
             ["3. Realistic timeline", "See section 3 below.", "P"],
             ["4. Right budget band", "Never quote-probe. Only if the caller volunteers a number: see section 4. No number mentioned = passes.", "C"],
             ["5. Decision-maker", "Passes when the caller speaks as the owner or tenant, or says the decider has authorised them. Flag if they signal someone else decides or they are only researching for someone. Never pushed on the call.", "C"]],
            [32, 112, 26], status_col=2)]

# 3 timeline
S += [Paragraph("3. Timeline rule (refined 9 October)", h1),
      P("Design takes 3 to 4 weeks and building 8 to 16 weeks (services.md). The files disagree on the minimum: services.md says a project that must be READY in under 6 weeks cannot be started, qualified.md says 8 to 10 weeks. We set 6 weeks as the hard limit and 6 to 10 weeks as a flag.", body), Spacer(1, 2 * mm),
      table([["What the caller says", "Example", "Result"],
             ["A START date", "'I can start tomorrow', 'as soon as possible'", "Fine. Not a deadline."],
             ["A POSSESSION / handover date", "'I get the keys next month'", "Fine. The work starts after possession anyway."],
             ["A FINISH date, 10 or more weeks away", "'ready by March'", "Fits."],
             ["A FINISH date, 6 to 10 weeks away", "'move in by 1 December'", "Fits, with a flag (tight; designer confirms)."],
             ["A FINISH date under 6 weeks, FIRM", "'finished in a month, fixed date'", "Decline, with the real reason given kindly."],
             ["A FINISH date under 6 weeks, flexible or firmness not said", "'a month, but I can stretch'", "Flag, not decline. The agent first asks: is it a firm date?"],
             ["No timing information at all", "'just starting to think'", "Flag."]],
            [58, 60, 52]),
      P("If the caller changes the date during the call, the latest date counts. Settings: MIN_LEAD_WEEKS = 6 and FLAG_LEAD_WEEKS = 10 in aangan/config.py. Status: PROPOSED, Nikhil to confirm the 6-week limit and the 6 to 10 week flag.", note)]

# 4 budget
S += [Paragraph("4. Budget fit (only when the caller volunteers a number)", h1),
      P("The implied rate is the volunteered budget (the TOP of any range, to protect good leads) divided by the area being designed, compared with the lowest price tier in pricing.md.", body), Spacer(1, 2 * mm),
      table([["Parameter", "Value", "Where", "Status"],
             ["Home floor (Standard tier)", "Rs 1,800 per sq ft", "pricing.md", "C"],
             ["Office floor (Basic tier)", "Rs 1,200 per sq ft", "pricing.md", "C"],
             ["Single or partial room floor", "Rs 3.5 lakh", "pricing.md", "C"],
             ["Decline below", "75% of the floor", "BUDGET_DECLINE_BELOW", "P"],
             ["Flag between", "75% and 100% of the floor", "same", "P"],
             ["Which end of a range", "The top (18-22 lakh counts as 22)", "classifier.py", "B"],
             ["No number mentioned", "Passes", "qualified.md", "C"]],
            [52, 52, 40, 26], status_col=3),
      P("Examples: 1 to 1.5 lakh for a kitchen and a bedroom is 43% of the room floor = decline. 18 to 22 lakh for 1,300 sq ft is about 94% of the home floor = flag.", note)]

# 5 scope
S += [Paragraph("5. Scope: what Aangan does and does not do", h1),
      table([["In scope", "Out of scope"],
             ["Apartment, villa or house in Pune or PCMC. Full home (2BHK onwards), a full floor, 2 or more rooms, or one complete room (bedroom or living room), always with execution.",
              "Advice or ideas only; decor and styling only; standalone furniture sourcing; Vastu-only consultation."],
             ["Offices, clinics and studios up to about 3,000 sq ft. An office above 3,000 sq ft is declined (now enforced in code).",
              "Architecture, moving walls, any structural work or permits."],
             ["Rented homes, if there is no structural change and the landlord agrees.",
              "Restaurants, hotels, retail shops, gyms. Anything outside Pune and PCMC."],
             ["Single-room job, with design, materials, furniture and execution included.", "A finish date firmly under 6 weeks away."]],
            [85, 85]),
      P("Open question for Nikhil: is there a minimum size for an office? His front desk declined a 180 sq ft pod citing 500 sq ft, which is in none of his files. Currently no minimum is enforced and such a lead is flagged.", note)]

S.append(PageBreak())
# 6 price
S += [Paragraph("6. What the agent may say about price", h1),
      P("<b>Decision by Milind: the agent may speak an indicative range.</b> This goes against the note in pricing.md ('no number should be quoted'), so Nikhil MUST approve it before go-live. The agent speaks ranges only when the caller asks about cost, always with the disclaimer, never multiplied into a total, never a discount.", body), Spacer(1, 2 * mm),
      table([["Project type", "Range the agent may say", "Source", "Status"],
             ["Whole or part home", "Rs 1,800 to 3,500 per sq ft of carpet area (luxury is higher)", "pricing.md", "P"],
             ["One room, all in", "Rs 3.5 to 8 lakh", "pricing.md", "P"],
             ["Office, clinic, studio", "Rs 1,200 to 4,000 per sq ft", "pricing.md", "P"]],
            [38, 78, 28, 26], status_col=3),
      P("<b>Disclaimer, said every time:</b> 'This is only an indicative range, not an exact price. Your designer will confirm the actual cost at the consultation, after seeing the site and the materials you choose.'", body),
      P("Where it lives: the Money section of prompts/voice_agent.md. To remove quoting, edit that section.", note)]

# 7 voice agent
S += [Paragraph("7. Voice agent parameters", h1),
      table([["Parameter", "Value", "Status"],
             ["Platform and agent", "Vaani. Agent 'aangan-enquiry-agent'.", "B"],
             ["Maximum call length", "5 minutes (protects the test credit; about Rs 28 per call at most)", "B"],
             ["Greeting", "'Hello, thank you for calling Aangan Studio. How can I help you today?'", "B"],
             ["Language", "English with automatic detection; replies in the caller's language (English, Hindi or a mix)", "B"],
             ["Idle hang-up", "Warning after 10 seconds of silence, hang-up after 20", "B"],
             ["Voice", "Cartesia voice 'devansh' (Vaani default, can be changed in Voice Lab)", "B"],
             ["Questions per turn", "At most ONE. Never two joined by 'and' or 'or'.", "B"],
             ["After an answer", "Says 'Okay' or 'Got it' and moves on. NEVER repeats back the phone number, name, size or date, and gives no recap at the end.", "B"],
             ["Never asked", "Budget (never probed or hinted), style details, appliances, technology, compliance, finances, brand", "C"],
             ["Decision-maker", "Asked once at most, lightly. Never pushed.", "C"],
             ["Not a fit", "Says exactly: 'This sounds like it may not be the right fit for us right now, but feel free to reach out if your timeline or scope changes.' (with the real reason first when it is a firm short deadline)", "C"],
             ["Complaints", "Stays polite, takes name and number, says 'I am passing this to our team right away', ends the call. No callback time promised.", "C"],
             ["Never commits to", "Dates, scope, prices, discounts, designer names, response times", "C"],
             ["Never says aloud", "'qualified', 'bucket', 'score', labels, tool names, section names", "B"]],
            [38, 108, 24], status_col=2)]
S += [Paragraph("Questions it asks, in order of importance", h2),
      table([["Home", "Office"],
             ["Must ask: name; phone number; home or office; area in Pune; whether they want design AND execution and what; when they need it finished. "
              "Then: flat or house and rough size; lived in or possession soon; own or rent (landlord OK if rented); whole home or certain rooms; when to start.",
              "Must ask: the business in a line; rough size and whether bare shell or fitted; how many people; which spaces (workstations, cabins, meeting room, pantry); when operational."],
             ["If time (only when the caller is chatty): what drives the date; who lives there and anything to keep in mind; living there during the work; a look they like or furniture to keep; how they heard of us; calls or WhatsApp.",
              "If time: own or lease and free to make changes; people expected in 2 to 3 years; who signs off; how they heard of us."]],
            [85, 85])]

# 8 booking
S += [Paragraph("8. Booking a consultation (Cal.com)", h1),
      table([["Parameter", "Value", "Status"],
             ["Event type", "'Design consultation', 30 minutes, via Cal.com (event type id 7412359)", "B"],
             ["Hours offered", "Monday to Saturday, 10:00 to 19:00, India time (the front desk's hours). No Sunday.", "P"],
             ["Minimum notice", "24 hours", "P"],
             ["Slots offered to a caller", "Real free times only; up to 3 per day, spread across the day; up to 4 days ahead", "B"],
             ["Who is offered booking", "Only callers who fit. Never a declined caller or a complaint.", "C"],
             ["Tool: create_slot", "Looks up free times, books nothing. Input: preferred_date (optional, YYYY-MM-DD).", "B"],
             ["Tool: create_booking", "Books the chosen time. Inputs: start (exact value from create_slot), name, phone; email OPTIONAL and never insisted on.", "B"],
             ["No email given", "A placeholder address is used because Cal.com requires one", "B"],
             ["Time taken meanwhile", "The agent is given fresh times; it never promises a time if booking fails", "B"],
             ["Meeting place", "Cal.com default (video). A real consultation may be a site visit: to decide with Nikhil.", "P"]],
            [38, 108, 24], status_col=2),
      P("Limit: a free Cal.com account is ONE calendar. Nikhil's 14 designers need team scheduling (a paid Cal.com feature) so consultations spread across designers.", note)]

# 9 handoff
S += [Paragraph("9. Designer handoff and CRM", h1),
      table([["Parameter", "Value", "Status"],
             ["Telegram group", "Private group. Every lead is posted.", "B"],
             ["Posted with a Claim button", "FORWARD, FORWARD_WITH_FLAG, NEEDS_HUMAN. First to press wins; who and when are recorded.", "B"],
             ["Posted as quiet FYI, no button", "DECLINE and NOT_CLASSIFIED (to a separate group if one is set)", "P"],
             ["Reminder if unclaimed", "After 30 minutes, then every 30 minutes, at most 6 times", "P"],
             ["Big project marker", "Home over 3,000 sq ft or office over 2,000 sq ft: message starts 'BIG PROJECT - tell Nikhil', HubSpot deal High priority", "P"],
             ["Message contents", "Caller, phone, area, type, site status, owner or tenant, scope and size, rooms wanted, household notes, needed by, who decides, volunteered budget, referral, outcome and flags, booked slot, recording link. No transcript.", "B"],
             ["HubSpot contact", "Every caller, declines included (with the reason in a note). Found by phone number (+91 format), so a repeat caller is never duplicated; a later decline never overwrites an Open status.", "B"],
             ["HubSpot lead status", "Forward and Flag = Open; Needs human = In progress; Decline = Unqualified; Not classified = New", "B"],
             ["HubSpot deal", "Forward and Flag only. Pipeline 'Sales Pipeline', stage 'New enquiry'. Priority High if referred or a big project, else Medium. Carries the handoff note. No price is ever stored.", "B"]],
            [42, 104, 24], status_col=2)]

# 10 data
S += [Paragraph("10. What is saved for every call", h1),
      P("Caller name, phone, area, home or office, scope summary, size, timeline in the caller's words, who decides, volunteered budget (never prompted), referral, site status, owner or tenant, language, rooms wanted, household notes, headcount, contact preference, business description, whether they asked about price; the full transcript and the recording link; the outcome, one-line reason, flags, the evidence quote for each criterion and the handoff note; start time (measured from Vaani's events), first-response time, notified and claimed times and who claimed; the booked slot; voice cost, AI cost and call length. Anything the caller did not say is saved as 'not given', never guessed.", body)]

# 11 costs
S += [Paragraph("11. Cost parameters", h1),
      table([["Parameter", "Value", "Status"],
             ["Classifier model", "Gemini Flash (gemini-3.8-flash)", "B"],
             ["Model price used for the estimate", "USD 0.30 per million input tokens, USD 2.50 per million output tokens (to be checked against Google's current price page)", "P"],
             ["Cost per enquiry (measured)", "About USD 0.0018 for classification", "B"],
             ["Voice cost", "Rs 5.60 per minute (the estimate Vaani shows on the agent page)", "B"],
             ["Exchange rate used", "Rs 88 per US dollar (a guess; check before trusting the dashboard)", "P"],
             ["Hosting and database", "Supabase free plan; Vercel free plan; HubSpot free CRM; Cal.com free plan", "B"]],
            [48, 98, 24], status_col=2)]

S.append(PageBreak())
# 12 open items
S += [Paragraph("12. Open items for Nikhil", h1),
      P("These are the places where his files were silent or contradicted each other, or where we added something he did not ask for. Each one is currently set to the proposal shown.", body), Spacer(1, 2 * mm),
      table([["#", "Question", "Currently set to"],
             ["1", "qualified.md says 'fails one: close gracefully' and also 'two or more fail: decline'. Which?", "A hard fail on criterion 1, 2 or 3 declines on its own. Unclear on 5 flags."],
             ["2", "services.md: cannot start a project that must be ready in under 6 weeks. qualified.md: 8 to 10 weeks. Which governs?", "Under 6 weeks (firm) = decline; 6 to 10 = flag."],
             ["3", "Is a caller who needs a FINISH date under 6 weeks always declined, or flagged when the date is flexible?", "Firm = decline; flexible or unclear = flag."],
             ["4", "Is there a minimum office size (180 sq ft pod declined for '500 sq ft')?", "No minimum; flagged."],
             ["5", "Is a budget a little under the standard rate a flag or a decline? Where is the line?", "75% of the floor."],
             ["6", "May the agent speak price ranges, given pricing.md says never to quote?", "Yes, with the disclaimer (Milind's decision)."],
             ["7", "Should 'just exploring' leads be flagged or declined?", "Flagged."],
             ["8", "Should declined leads also go to designers, as a quiet FYI?", "Yes, as FYI with no claim button."],
             ["9", "Big-project sizes that should alert Nikhil.", "Home over 3,000, office over 2,000 sq ft."],
             ["10", "Reminder timing for unclaimed leads.", "30 minutes, up to 6 times."],
             ["11", "Consultation hours, notice period and whether it is a video call or a site visit.", "Mon to Sat 10-19, 24 h notice, video."],
             ["12", "One shared calendar or one per designer (needs a paid Cal.com plan)?", "One calendar."],
             ["13", "Should the agent read numbers back to avoid mishearing, or never repeat (Milind's choice)?", "Never repeat."]],
            [8, 100, 62]),
      Paragraph("13. Where each setting lives", h1),
      table([["What", "File"],
             ["Numbers: thresholds, rates, reminder times, stage and event ids", "aangan/config.py"],
             ["What the caller hears (all agent behaviour, questions, price ranges, close)", "prompts/voice_agent.md, prompts/booking_on.md (applied with tools/vaani_agent.py)"],
             ["How a finished call is read and judged", "prompts/classify.md and aangan/classifier.py"],
             ["The written rubric and its reasoning", "rubric.md, services.md, qualified.md, pricing.md"],
             ["Telegram, HubSpot, Cal.com behaviour", "aangan/telegram.py, aangan/hubspot.py, aangan/booking.py, aangan/calcom.py"],
             ["Everything that happens when a call ends", "aangan/pipeline.py and api/vaani_webhook.py"],
             ["What was built, what broke, what was learned", "BUILD_LOG.md"]],
            [92, 78])]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="Aangan Studio Phone Enquiry Agent: all parameters", author="Milind")
doc.build(S, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT, OUT.stat().st_size, "bytes")
