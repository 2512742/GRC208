"""Vercel entry point: exposes the FastAPI app as a Python serverless function.

vercel.json rewrites every /api/* request here. The backend package lives in ../backend.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
