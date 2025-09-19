"""Utility helpers for the HTTP server."""

from __future__ import annotations

import secrets
from datetime import datetime


def generate_upload_filename() -> str:
    """Generate a unique upload filename with UTC timestamp and random hex.
    
    Format: upload_<YYYYMMDD>_<HHMMSS>_<6hex>.json
    """
    now = datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    random_hex = secrets.token_hex(3)  # 6 characters
    return f"upload_{date_str}_{time_str}_{random_hex}.json"
