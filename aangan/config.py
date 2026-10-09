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
