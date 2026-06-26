import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-opus-4-5"


def generate_brief(emails: list, events: list, upcoming: list, inbox_items: list, recruiter_emails: list = None, linkedin_jobs: list = None) -> dict:
    today_events_text = _fmt_events(events)
    upcoming_text = _fmt_upcoming(upcoming)
    emails_text = _fmt_emails(emails)
    inbox_text = _fmt_inbox(inbox_items)
    recruiter_text = _fmt_recruiter_emails(recruiter_emails or [])
    jobs_text = _fmt_jobs(linkedin_jobs or [])

    prompt = f"""You are a sharp, concise chief of staff. Your job is to brief your boss each morning so they know exactly what matters today and can focus without overwhelm.

Here is everything you know about their day:

=== TODAY'S CALENDAR ===
{today_events_text or "Nothing scheduled today."}

=== COMING UP (next 3 days) ===
{upcoming_text or "Nothing significant coming up."}

=== UNREAD EMAILS (most recent first) ===
{emails_text or "Inbox clear."}

=== THEIR PERSONAL INBOX (things they've dumped in to deal with) ===
{inbox_text or "Nothing in the inbox."}

=== RECRUITER EMAILS (last 7 days) ===
{recruiter_text or "No recruiter emails found."}

=== NEW PMM JOBS ON LINKEDIN (last 24h) ===
{jobs_text or "No new listings found."}

---

Your job:
1. Write a SHORT (2-3 sentence) plain-English summary of the day. Be direct. No fluff.
2. Pick up to 3 emails that genuinely need action today (ignore newsletters, automated stuff, FYIs).
3. Propose exactly 3 priorities for the day. Each priority should have a clear title, a one-sentence reason why it matters TODAY (not just generally), and a rough time suggestion. Be opinionated — don't hedge.
4. Identify anything on the watchlist (things to keep an eye on, not act on yet).
5. Write a one-sentence heads-up about the next few days.
6. Summarise the top job opportunities — recruiter emails worth replying to, and LinkedIn listings that look promising. Be selective, not exhaustive.

Respond in this exact JSON format:
{{
  "summary": "...",
  "email_highlights": [
    {{"from": "...", "subject": "...", "action": "..."}}
  ],
  "priorities": [
    {{"title": "...", "reasoning": "...", "source": "email|calendar|inbox|manual", "suggested_time": "morning|afternoon|anytime"}}
  ],
  "watchlist": ["...", "..."],
  "fyi": "...",
  "job_opportunities": [
    {{"type": "recruiter|linkedin", "title": "...", "company": "...", "note": "...", "url": ""}}
  ]
}}

Keep everything tight. Your boss doesn't have time for waffle."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "summary": raw[:500],
            "email_highlights": [],
            "priorities": [],
            "watchlist": [],
            "fyi": "",
            "job_opportunities": []
        }


def triage_items(items: list) -> list:
    """
    For a list of raw inbox items (just text), ask the AI to categorise
    and suggest what to do with each one.

    Returns the items list with ai_suggestion, ai_reasoning, and category added.
    """
    if not items:
        return []

    items_text = "\n".join(
        f"{i+1}. [{item['id']}] {item['content']}" for i, item in enumerate(items)
    )

    prompt = f"""You are a GTD-style chief of staff. The user has dumped these items into their inbox.
For each one, decide:
- category: task | event | idea | reference | delegate | delete
- suggestion: do_now | schedule | someday | delegate | delete
- reasoning: one SHORT sentence on why

Items:
{items_text}

Respond in this exact JSON format — an array, one entry per item, using the bracketed ID:
[
  {{
    "id": 1,
    "category": "task",
    "suggestion": "do_now",
    "reasoning": "..."
  }}
]

Only output the JSON array. No other text."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        suggestions = json.loads(raw)
        # Map suggestions back onto items by position
        suggestion_map = {s["id"]: s for s in suggestions}
        for i, item in enumerate(items):
            s = suggestion_map.get(i + 1, {})
            item["ai_suggestion"] = s.get("suggestion", "")
            item["ai_reasoning"] = s.get("reasoning", "")
            item["category"] = s.get("category", "")
    except Exception:
        pass  # return items as-is if AI fails

    return items


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_events(events: list) -> str:
    if not events:
        return ""
    lines = []
    for e in events:
        line = f"- {e['time']}: {e['title']}"
        if e.get("attendees"):
            line += f" (with {e['attendees']})"
        lines.append(line)
    return "\n".join(lines)


def _fmt_upcoming(events: list) -> str:
    if not events:
        return ""
    return "\n".join(f"- {e['when']}: {e['title']}" for e in events)


def _fmt_emails(emails: list) -> str:
    if not emails:
        return ""
    lines = []
    for e in emails:
        lines.append(f"- From {e['from']} | {e['subject']} | {e['date']}\n  {e['snippet']}")
    return "\n".join(lines)


def _fmt_inbox(items: list) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item['content']}" for item in items)


def _fmt_recruiter_emails(emails: list) -> str:
    if not emails:
        return ""
    lines = []
    for e in emails:
        lines.append(f"- From {e['from']} | {e['subject']}\n  {e['snippet']}")
    return "\n".join(lines)


def _fmt_jobs(jobs: list) -> str:
    if not jobs:
        return ""
    lines = []
    for j in jobs:
        line = f"- {j['title']} at {j['company']}"
        if j.get("location"):
            line += f" ({j['location']})"
        if j.get("url"):
            line += f" — {j['url']}"
        lines.append(line)
    return "\n".join(lines)
