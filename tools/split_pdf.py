"""Split the September enquiries PDF into one text file per enquiry (T01..T20, W01..W10, F01..F10)."""
import re, sys
from pathlib import Path
import pypdf

PDF = Path("Aangan_Sep 2026_Enquiries.pdf")
OUT = Path("enquiries")

text = "\n".join(p.extract_text() for p in pypdf.PdfReader(PDF).pages)
text = re.sub(r"\s+", " ", text)  # PDF has one word per line; flatten


parts = re.split(r"(?=\b[TWF]\d\d · (?:Phone|WhatsApp|Web Form))", text)
count = 0
for part in parts:
    m = re.match(r"([TWF]\d\d) · ", part)
    if not m:
        continue
    eid = m.group(1)
    body = re.split(r"\sSECTION \d", part)[0].strip()  # cut off the next section banner
    # one line per speaker turn / timestamped message / note
    body = re.sub(r"\s(?=(Front Desk|Caller|Note|\d{1,2} Sept,|\[No reply|Status:|First call|Second call|Missed call))", "\n", body)
    body = re.sub(r"\s(?=(Name:|Phone:|Email:|Project type:|Location:|Carpet area:|Current state:|Timeline:|Budget:|How did you find us:|Notes:))", "\n", body) if eid.startswith("F") else body
    (OUT / f"{eid}.txt").write_text(body + "\n", encoding="utf-8")
    count += 1
print(count, "files written")
