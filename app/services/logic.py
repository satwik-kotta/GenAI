import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def decide_activity(weather: str, activity: str, fallback: str) -> str:
    if weather == "Rain":
        return fallback
    return activity


def _next_weekend_day(today: date) -> date:
    days_until_saturday = (5 - today.weekday()) % 7
    return today + timedelta(days=days_until_saturday)


def _resolve_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        # Fallback prevents hard failure when system tz database is missing.
        return ZoneInfo("UTC")


def resolve_time_window(time_text: str | None, tz_name: str = "Asia/Kolkata") -> tuple[str, str]:
    tz = _resolve_timezone(tz_name)
    today = date.today()
    target_date = _next_weekend_day(today) if time_text and "weekend" in time_text.lower() else today

    start_hour = 10
    end_hour = 14

    if time_text:
        match = re.search(
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-|until)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            time_text.lower(),
        )
        if match:
            s_h, s_m, s_ampm, e_h, e_m, e_ampm = match.groups()
            start_hour = int(s_h)
            start_min = int(s_m or 0)
            end_hour = int(e_h)
            end_min = int(e_m or 0)

            if s_ampm == "pm" and start_hour != 12:
                start_hour += 12
            if s_ampm == "am" and start_hour == 12:
                start_hour = 0
            if e_ampm == "pm" and end_hour != 12:
                end_hour += 12
            if e_ampm == "am" and end_hour == 12:
                end_hour = 0

            if not e_ampm and not s_ampm and end_hour <= start_hour:
                end_hour += 12
        else:
            start_min = 0
            end_min = 0
    else:
        start_min = 0
        end_min = 0

    start_dt = datetime.combine(target_date, time(start_hour, start_min), tzinfo=tz)
    end_dt = datetime.combine(target_date, time(end_hour % 24, end_min), tzinfo=tz)

    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=4)

    return start_dt.isoformat(), end_dt.isoformat()
