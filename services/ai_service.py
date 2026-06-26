import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-opus-4-5"


def generate_brief(emails: list, events: list, upcoming: list, inbox_items: list) -> dict:
    """
    Given today's emails, calendar events, and dump inbox items,
    generate a morning brief and propose up to 3 priorities.

    Returns:
        {
            "summary": str,          # 2-3 sentence overview of the day
            "email_highlights": [...], # key emails worth actioning
            "priorities": [          # up to 3 proposed priorities
                {
                    "title": str,
                    "reasoning": str,
                    "source": str,   # "email" | "calendar" | "inbox" | "manual"
                    "suggested_time": str  # e.g. "morning" | "afternoon" | "anytime"
                }
            ],
            "watchlist": [...],      # things to keep an eye on but not act on today
            "fyi": str               # short note about the next few days
        }
    """

    today_events_text = _fmt_events(events)
    upcoming_text = _fmt_upcoming(upcoming)
    emails_text = _fmt_emails(emails)
    inbox_text = _fmt_inbox(inbox_items)

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

---

Your job:
1. Write a SHORT (2-3 sentence) plain-English summary of the day. Be direct. No fluff.
2. Pick up to 3 emails that genuinely need action today (ignore newsletters, automated stuff, FYIs).
3. Propose exactly 3 priorities for the day. Each priority should have a clear title, a one-sentence reason why it matters TODAY (not just generally), and a rough time suggestion. Be opinionated — don't hedge.
4. Identify anything on the watchlist (things to keep an eye on, not act on yet).
5. Write a one-sentence heads-up about the next few days.

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
  "fyi": "..."
}}

Keep everything tight. Your boss doesn't have time for waffle."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return the raw text wrapped in a basic structure
        return {
            "summary": raw[:500],
            "email_highlights": [],
            "priorities": [],
            "watchlist": [],
            "fyi": ""
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
