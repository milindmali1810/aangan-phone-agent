"""Every business setting in ONE place. Change a number here and the classifier follows.

Items marked ASSUMPTION are Milind's/Claude's proposals that Nikhil has not confirmed yet.
"""

MODEL = "gemini-3.8-flash"

# Rough price per million tokens in US dollars. ASSUMPTION: check Google's current price page before
# trusting the cost numbers on the dashboard.
PRICE_PER_M_INPUT_USD = 0.30
PRICE_PER_M_OUTPUT_USD = 2.50

# A2 (timeline). Weeks until the work must START or be READY.
MIN_LEAD_WEEKS = 6        # under this: DECLINE (services.md hard minimum)
FLAG_LEAD_WEEKS = 10      # from MIN to this: FORWARD_WITH_FLAG (qualified.md says 8-10)

# Budget fit (rubric.md section 2). Only used when the caller volunteers a number.
BUDGET_DECLINE_BELOW = 0.75   # ASSUMPTION: below 75% of the lowest tier floor = DECLINE
HOME_FLOOR_PER_SQFT = 1800        # Standard residential tier, lowest
OFFICE_FLOOR_PER_SQFT = 1200      # Basic commercial tier, lowest
ROOM_FLOOR_LAKH = 3.5             # Single-room redesign, lowest
# Use the top of a volunteered range ("18-22 lakh" -> 22). This protects good leads from being
# wrongly declined, which is the costliest mistake.
BUDGET_USE = "upper"

# Big-deal alert to Nikhil. ASSUMPTION.
BIG_HOME_SQFT = 3000
BIG_OFFICE_SQFT = 2000

# Commercial size limit from services.md.
MAX_COMMERCIAL_SQFT = 3000

# Whether the voice agent may speak price ranges (Milind's decision, needs Nikhil's approval).
QUOTE_PRICE_RANGE = True

# Voice cost. The rate comes from the Vaani agent page (an estimate); the exchange rate is a guess.
# Check both before trusting the dashboard's voice cost.
VOICE_RATE_INR_PER_MIN = 5.6  # Vaani shows "Rs 5.60/min (est.)" on the agent page
INR_PER_USD = 88.0

# HubSpot. New deals start in this stage of the default "Sales Pipeline". The free plan allows one pipeline, and its
# first stage was named "Appointment Scheduled", which was misleading, so Milind had it renamed to "New enquiry". See the
# BUILD_LOG for the new stage id.
HUBSPOT_DEAL_STAGE = "4417021666"  # "New enquiry" (renamed from Appointment Scheduled; HubSpot issued a new id)

# Telegram handoff. REPING_MINUTES is Milind's proposal to Nikhil, not Nikhil's rule.
REPING_MINUTES = 30   # re-ping the group if a lead is still unclaimed after this long
REPING_MAX = 6        # stop after this many reminders so a forgotten lead cannot spam the group all night

# Cal.com consultation event type (created by tools/cal_setup.py). Mon-Sat 10:00-19:00 India time, 30 minutes, 24 hours' notice (proposal).
CAL_EVENT_TYPE_ID = 7412359
