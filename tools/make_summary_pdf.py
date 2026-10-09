"""Builds Aangan_Phone_Agent_Summary.pdf: the one-page-style project summary for Notion / review.  Contains no keys or passwords.
   python tools/make_summary_pdf.py"""
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "Aangan_Phone_Agent_Summary.pdf"
INK, MUTED, LINE, HEAD, ACCENT = (colors.HexColor(c) for c in ("#1b1b1a", "#6b6a66", "#d9d8d2", "#1f3a5f", "#2a78d6"))
ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=1.5)
title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=HEAD)
h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=HEAD, spaceBefore=11, spaceAfter=4)
mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8.6, leading=11.5)


def rich(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r'<font name="Courier" size="8.6">\1</font>', t)
    return t


def P(t, st=body):
    return Paragraph(rich(t), st)


def bullets(items, numbered=False):
    return [Paragraph(rich(t), bullet, bulletText=(f"{i}." if numbered else "\u2022")) for i, t in enumerate(items, 1)]


S = [P("Aangan Studio: phone enquiry agent", title), Spacer(1, 3 * mm)]
box = Table([[P("**One line:** callers phone Aangan; a voice agent answers day and night, asks a few questions, and every call is judged against Nikhil's rubric, "
                "logged, sent to the designers (Telegram + HubSpot), and booked into a consultation slot.")]], colWidths=[174 * mm])
box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3fa")), ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
                         ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
S.append(box)

S += [P("How it flows", h2), P("Caller > Vaani voice agent (Gemini brain, asks questions, offers real slots via Cal.com) > call ends > Vaani webhook > our server on Vercel > "
                              "Gemini Flash reads the transcript, plain code applies the rules > saved in Supabase with cost > Telegram (Claim button + transcript) + "
                              "HubSpot (contact + deal) + email (if a consultation was booked) > dashboard.")]

S += [P("Outcomes (5)", h2), P("Forward | Forward with flag | Decline | Needs a human (complaint) | Not classified (missed call). Every lead is logged, declines too.")]

S += [P("Key decisions and why", h2)] + bullets([
    "Plain code applies the rules, the AI only extracts facts with quotes: auditable.",
    "Cheaper model (Gemini Flash) is enough because the rules are written down (about $0.002 per call).",
    "Timeline: a START or POSSESSION date is never a deadline; only a firm FINISH date under 6 weeks declines.",
    "The agent may speak price ranges with a disclaimer (my decision; Nikhil must approve, pricing.md says never quote).",
    "Telegram for handoff: instant, Claim button so two designers don't both call. Email = backup.",
    "Log declined callers too, so Nikhil can audit the rules.",
    "Agent never repeats back what the caller says; one question per turn; never asks for an email (spoken emails are misheard)."])

S += [P("Status (10 Oct 2026): 64 live checks pass, 0 fail, 79 test checks pass", h2),
      P("**Proven live:** classifier, database, dashboard (password) with transcript + recording, Telegram, HubSpot, email after a booking (simulated), Cal.com slots."),
      Spacer(1, 1.5 * mm),
      P("**NOT proven:** Vaani's booking tool booking during a real voice call (needs one call, about Rs 12-17).")]

S += [P("Bugs found on the way (lessons)", h2)] + bullets([
    "Vaani chat panel cannot run tools; test booking by VOICE only.",
    "Vaani reports tool \"success\" even when Cal.com refused; trust Cal.com.",
    "Cal.com refuses emails that cannot receive mail (example.com); use a real team mailbox.",
    "Vaani page \"Save Agent\" restores old settings; refresh first, avoid saving.",
    "Anything written in an agent prompt can be spoken: keep internal labels out."])

links = [["Dashboard", "https://aangan-webhook.vercel.app/  (password: see DASHBOARD_PASSWORD in .env)"],
         ["Status file", "https://aangan-webhook.vercel.app/SYSTEM_STATUS.md"],
         ["Code (private)", "https://github.com/milindmali1810/aangan-phone-agent"],
         ["Folder", "D:\\Dekh le - Designer  (BUILD_LOG.md, rubric.md, Aangan_Phone_Agent_Parameters.pdf)"],
         ["Vaani agent", "aangan-enquiry-agent  (d895b0e0-cff7-476b-9c5e-afcc2b02fce9)"],
         ["Supabase project", "aangan-phone-agent  (oeelqidjxszikigtdixs), Mumbai"],
         ["HubSpot / Cal.com", "HubSpot portal 247643487, stage \"New enquiry\"; Cal.com event \"Design consultation\" (7412359)"],
         ["Telegram / Vercel", "Bot @aangan_leads1810_bot; Vercel project aangan-webhook"],
         ["Re-check any time", "python tools/verify_all.py --tests"]]
t = Table([[P(f"**{a}**"), P(b)] for a, b in links], colWidths=[34 * mm, 140 * mm])
t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f6f6f3")),
                       ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
S += [KeepTogether([P("Links and IDs (no secrets)", h2), t])]

S += [KeepTogether([P("To do before real customers", h2)] + bullets([
    "Nikhil confirms the proposed rules (13 open questions, last page of the parameters PDF).",
    "Rotate every key that was pasted in chat (Gemini, Supabase, Vaani, HubSpot, Cal.com, Telegram, Resend + webhook/booking/cron/dashboard secrets).",
    "Delete test data (3 \"Asha\" test leads; the 40 sample rows are marked as samples).",
    "Real Indian phone number (not confirmed in Vaani docs); WhatsApp/SMS confirmation to the caller; verified email domain.",
    "Free Cal.com = one calendar; 14 designers need team scheduling.",
    "Telegram optimisation (yours, later).",
    "Explain it to Nikhil: the Cut (what we deliberately did not build), why Telegram, why log declines, why a cheaper model; how WhatsApp and the web form plug in at the \"receive an enquiry\" step."], numbered=True))]


def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(MUTED)
    c.drawString(18 * mm, 10 * mm, "Aangan Studio phone enquiry agent - summary (no keys or passwords inside)")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}"); c.restoreState()


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                  title="Aangan Studio phone enquiry agent: summary", author="Milind").build(S, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
