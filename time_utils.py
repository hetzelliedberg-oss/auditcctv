"""
Bangkok Timezone (UTC+7) Utilities
Guarantees consistent Thailand timestamps across local machines and cloud containers (Streamlit Cloud).
"""
from datetime import datetime, timezone, timedelta

TZ_BANGKOK = timezone(timedelta(hours=7))

def now_bkk() -> datetime:
    """Returns the current datetime in Bangkok (UTC+7)."""
    return datetime.now(TZ_BANGKOK)

def bkk_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Returns current Bangkok timestamp as a formatted string."""
    return now_bkk().strftime(fmt)

def bkk_time_str() -> str:
    """Returns current Bangkok time (HH:MM:SS)."""
    return now_bkk().strftime("%H:%M:%S")

def from_timestamp_bkk(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Converts a POSIX timestamp (e.g. from os.path.getmtime) to Bangkok time string."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(TZ_BANGKOK)
    return dt.strftime(fmt)
