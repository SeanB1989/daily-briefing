from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def build_calendar(creds: Credentials):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_todays_events(creds: Credentials) -> list[dict]:
    """Fetch all calendar events for today."""
    service = build_calendar(creds)

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e.get("start", {})
        end = e.get("end", {})

        # Handle all-day events vs timed events
        if "dateTime" in start:
            start_str = _fmt_time(start["dateTime"])
            end_str = _fmt_time(end["dateTime"])
            time_str = f"{start_str} – {end_str}"
            all_day = False
        else:
            time_str = "All day"
            all_day = True

        events.append({
            "id": e.get("id"),
            "title": e.get("summary", "(no title)"),
            "time": time_str,
            "all_day": all_day,
            "location": e.get("location", ""),
            "description": (e.get("description", "") or "")[:150],
            "attendees": _fmt_attendees(e.get("attendees", [])),
        })

    return events


def get_upcoming_events(creds: Credentials, days: int = 3) -> list[dict]:
    """Fetch events for the next N days (excluding today) — useful for context."""
    service = build_calendar(creds)

    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = tomorrow + timedelta(days=days)

    result = service.events().list(
        calendarId="primary",
        timeMin=tomorrow.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=10
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e.get("start", {})
        if "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"])
            day_str = dt.strftime("%a %d %b")
            time_str = dt.strftime("%H:%M")
            when = f"{day_str} at {time_str}"
        else:
            date_str = start.get("date", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                when = dt.strftime("%a %d %b (all day)")
            except Exception:
                when = date_str

        events.append({
            "title": e.get("summary", "(no title)"),
            "when": when,
        })

    return events


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%H:%M")
    except Exception:
        return iso


def _fmt_attendees(attendees: list) -> str:
    if not attendees:
        return ""
    names = [a.get("displayName") or a.get("email", "") for a in attendees[:4]]
    result = ", ".join(names)
    if len(attendees) > 4:
        result += f" +{len(attendees) - 4} more"
    return result
