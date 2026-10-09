"""Read a setting from the real environment (on Vercel) or from the local .env file."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get(name, default=None):
    if os.environ.get(name):
        return os.environ[name]
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return default
