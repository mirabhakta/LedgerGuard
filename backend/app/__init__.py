"""LedgerGuard application package and local environment bootstrap."""

from pathlib import Path

from dotenv import load_dotenv


# Explicit shell/deployment variables win; .env is only a local-development fallback.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

