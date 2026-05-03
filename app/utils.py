"""Utility functions."""
from datetime import datetime, date, time, timedelta
from .models import Setting


def get_service_start_time():
    """Returns service start time as a `time` object (default 10:00)."""
    raw = Setting.get("service_start_time", "10:00") or "10:00"
    try:
        h, m = raw.split(":")
        return time(int(h), int(m))
    except Exception:
        return time(10, 0)


def determine_status(check_in_dt: datetime, service_d: date) -> str:
    """Decide on_time vs late based on configured service start time."""
    start_t = get_service_start_time()
    cutoff = datetime.combine(service_d, start_t)
    return "on_time" if check_in_dt <= cutoff else "late"


def upcoming_sunday(today=None):
    """Return the next Sunday (or today if today is Sunday)."""
    today = today or date.today()
    # weekday(): Mon=0 ... Sun=6
    days_ahead = (6 - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


def previous_sundays(n=12, until=None):
    """Return list of last n Sunday dates, most recent first."""
    until = until or date.today()
    # Find most recent Sunday on or before `until`
    last_sun = until - timedelta(days=(until.weekday() + 1) % 7)
    return [last_sun - timedelta(weeks=i) for i in range(n)]


def hk_now():
    """Return current datetime in Asia/Hong_Kong timezone (without tzinfo for SQLite simplicity)."""
    # Render servers run UTC; church operates in HKT (UTC+8). We store check-in as HKT naive.
    return datetime.utcnow() + timedelta(hours=8)


STATUS_LABELS = {
    "on_time": "準時",
    "late": "遲到",
}


def status_label(status):
    return STATUS_LABELS.get(status, status or "—")
