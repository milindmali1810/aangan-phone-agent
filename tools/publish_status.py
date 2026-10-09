"""Publishes SYSTEM_STATUS.md at https://aangan-webhook.vercel.app/SYSTEM_STATUS.md (anyone with the link can open it).
The public copy replaces personal email addresses; it contains no keys, tokens or passwords.   python tools/publish_status.py
Then commit and push: Vercel redeploys by itself."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = (ROOT / "SYSTEM_STATUS.md").read_text(encoding="utf-8")
s = re.sub(r"[A-Za-z0-9._-]+\+<phone>@gmail\.com", "<team mailbox>+<phone>@<team domain>", s)
s = re.sub(r"[A-Za-z0-9._+-]+@gmail\.com", "the team address", s)
(ROOT / "public").mkdir(exist_ok=True)
(ROOT / "public" / "SYSTEM_STATUS.md").write_text(s, encoding="utf-8")
print("public copy written;", "no @ left:", "@" not in s.replace("<team mailbox>+<phone>@<team domain>", ""))
