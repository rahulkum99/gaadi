from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


def parse_query_date(value, default="today"):
    today = timezone.localdate()
    if not value or value == default or value == "today":
        return today
    if value == "yesterday":
        return today - timedelta(days=1)
    parsed = parse_date(value)
    return parsed


def local_day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min), timezone.get_current_timezone())
    return start, start + timedelta(days=1)


def parse_history_range(params):
    today = timezone.localdate()
    kind = (params.get("range") or params.get("period") or "today").strip().lower()
    start = parse_date(params.get("from") or "") if params.get("from") else None
    end = parse_date(params.get("to") or "") if params.get("to") else None
    if kind == "yesterday":
        start = end = today - timedelta(days=1)
    elif kind in {"last_7", "last7", "7d"}:
        end = today
        start = today - timedelta(days=6)
    elif kind == "custom":
        if start is None or end is None:
            return None, None, "Custom range needs from and to dates."
    else:
        start = end = today
        if params.get("from") and start is None:
            return None, None, "Unknown date range."
    if start is None or end is None:
        return None, None, "Unknown date range."
    if end < start:
        return None, None, "End date must be on or after the start date."
    if (end - start).days > 31:
        return None, None, "Date range cannot exceed 31 days."
    return start, end, None


def date_span(start, end):
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days
