import base64
import re
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def build_gmail(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_important_emails(creds: Credentials, max_results: int = 15) -> list[dict]:
    """
    Fetch recent unread or important emails and return a clean summary list.
    We grab the sender, subject, snippet, and date — enough for the AI to work with.
    """
    service = build_gmail(creds)

    # Pull unread emails from inbox (not promotions/social)
    query = "is:unread in:inbox category:primary"
    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    emails = []

    for msg in messages:
        try:
            full = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
            snippet = full.get("snippet", "")

            # Parse a clean date string
            date_raw = headers.get("Date", "")
            date_clean = _parse_email_date(date_raw)

            emails.append({
                "id": msg["id"],
                "from": _clean_sender(headers.get("From", "Unknown")),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": snippet[:200],  # keep it short for the AI prompt
                "date": date_clean,
            })
        except Exception:
            continue  # skip any message that errors

    return emails


def _clean_sender(raw: str) -> str:
    """Extract just the name/email from a raw From header."""
    # "John Smith <john@example.com>" -> "John Smith"
    match = re.match(r'^"?([^"<]+)"?\s*<', raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _parse_email_date(raw: str) -> str:
    """Best-effort parse of an email Date header to a readable string."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%a %d %b, %H:%M")
    except Exception:
        return raw[:20] if raw else "Unknown date"
