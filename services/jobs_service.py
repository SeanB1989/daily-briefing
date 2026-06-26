import re
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ── LinkedIn public job scraper ───────────────────────────────────────────────

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SEARCH_PARAMS = {
    "keywords": "Product Marketing Manager",
    "location": "",
    "f_WT": "2,3",
    "f_TPR": "r86400",
    "start": 0,
    "count": 10,
}


def get_linkedin_jobs() -> list[dict]:
    """Scrape LinkedIn public job search for PMM roles (no login needed)."""
    try:
        resp = requests.get(
            LINKEDIN_SEARCH_URL,
            params=SEARCH_PARAMS,
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code != 200:
            return []

        html = resp.text
        jobs = []

        titles = re.findall(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', html, re.DOTALL)
        companies = re.findall(r'class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)
        locations = re.findall(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL)
        links = re.findall(r'href="(https://www\.linkedin\.com/jobs/view/[^"?]+)', html)

        for i in range(min(len(titles), len(companies), 8)):
            jobs.append({
                "title": _clean(titles[i]),
                "company": _clean(companies[i]) if i < len(companies) else "Unknown",
                "location": _clean(locations[i]) if i < len(locations) else "",
                "url": links[i] if i < len(links) else "",
            })

        return jobs

    except Exception:
        return []


# ── Recruiter email filter ────────────────────────────────────────────────────

RECRUITER_KEYWORDS = [
    "opportunity", "role", "position", "hiring", "job",
    "recruiter", "talent", "opening", "candidate", "interview",
    "your background", "your profile", "reached out", "exciting role",
]

RECRUITER_SENDER_PATTERNS = [
    "recruit", "talent", "hiring", "hr@", "people@", "careers@",
    "headhunt", "staffing", "linkedin"
]


def get_recruiter_emails(creds: Credentials, max_results: int = 20) -> list[dict]:
    """Pull emails that look like recruiter outreach from Gmail."""
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        query = (
            "in:inbox newer_than:7d ("
            "subject:opportunity OR subject:role OR subject:position OR "
            "subject:hiring OR subject:\"job opportunity\" OR "
            "subject:\"exciting opportunity\" OR subject:recruiter"
            ")"
        )

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
                sender = headers.get("From", "").lower()
                subject = headers.get("Subject", "")

                is_recruiter = (
                    any(p in sender for p in RECRUITER_SENDER_PATTERNS) or
                    any(k in snippet.lower() for k in RECRUITER_KEYWORDS) or
                    any(k in subject.lower() for k in RECRUITER_KEYWORDS)
                )

                if is_recruiter:
                    emails.append({
                        "from": _clean_sender(headers.get("From", "Unknown")),
                        "subject": subject,
                        "snippet": snippet[:200],
                    })
            except Exception:
                continue

        return emails

    except Exception:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def _clean_sender(raw: str) -> str:
    match = re.match(r'^"?([^"<]+)"?\s*<', raw)
    if match:
        return match.group(1).strip()
    return raw.strip()
