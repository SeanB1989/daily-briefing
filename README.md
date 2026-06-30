# Chief of Staff

Your personal AI-powered command centre. Dumps, briefs, priorities — no overwhelm.

Built with Python/Flask, Google APIs, and Anthropic Claude.

---

## What it does

- **Quick Dump** — capture anything from your head in seconds, from any page, without breaking your flow
- **Morning Brief** — AI reads your Gmail, Google Calendar, and personal inbox and tells you what actually matters today, with reasoning and a proposed top 3
- **Triage** — process your inbox with AI-generated suggestions; one decision per item (Do it, Schedule, Someday, Delegate, or Delete)
- **Job Search** — surfaces Product Marketing Manager (PMM) roles from LinkedIn and recruiter outreach from Gmail, directly in your morning brief

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Frontend | Jinja2 templates + Tailwind CSS |
| Database | SQLite (`chief.db`) |
| AI | Anthropic Claude (`claude-opus-4-5`) |
| Auth | Google OAuth 2.0 |
| APIs | Gmail API, Google Calendar API, Google People API |

---

## File structure

```
chief-of-staff/
├── main.py                  # Flask routes + OAuth flow
├── database.py              # SQLite schema + helpers
├── requirements.txt         # Python dependencies
├── services/
│   ├── ai_service.py        # Claude (brief generation + triage)
│   ├── gmail_service.py     # Gmail API integration
│   ├── calendar_service.py  # Google Calendar API integration
│   └── jobs_service.py      # LinkedIn scraping + recruiter email filter
└── templates/
    ├── base.html            # Core layout + persistent Quick Dump bar
    ├── login.html           # Google sign-in page
    ├── brief.html           # Morning brief view
    ├── dump.html            # Capture / inbox view
    └── triage.html          # AI triage view
```

---

## Setup (do this once)

### 1. Clone or create the project

```bash
git clone https://github.com/your-username/chief-of-staff.git
cd chief-of-staff
pip install -r requirements.txt
```

Or open in [Replit](https://replit.com) directly.

### 2. Set up Google Cloud (Gmail + Calendar access)

This is the fiddly bit, but you only do it once.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project
2. In **APIs & Services → Library**, enable:
   - **Gmail API**
   - **Google Calendar API**
   - **Google People API**
3. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**, fill in the app name and your email
   - Add scopes: `.../auth/gmail.readonly` and `.../auth/calendar.readonly`
   - Add yourself as a test user
4. Go to **Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorised redirect URI: `https://YOUR-APP-URL/oauth2callback`
   - Download the credentials JSON

### 3. Set environment variables

Create a `.env` file or (on Replit) add these as **Secrets**:

| Key | Value |
|-----|-------|
| `GOOGLE_CLIENT_ID` | From your downloaded credentials JSON |
| `GOOGLE_CLIENT_SECRET` | From your downloaded credentials JSON |
| `OAUTH_REDIRECT_URI` | `https://YOUR-APP-URL/oauth2callback` |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |
| `FLASK_SECRET_KEY` | Any random string |

### 4. Run

```bash
python main.py
```

Visit the app URL, click **Connect Google Account**, and you're in.

---

## Day-to-day use

**Morning** — open the app, hit "Generate my brief". Read it, confirm your top 3. Done in under 5 minutes.

**Throughout the day** — whenever something hits your brain, use the quick dump bar at the top. Don't think about where it goes — just dump it.

**Evening (or whenever)** — go to Triage, hit "Get AI suggestions", and burn through your inbox. One decision per item.

---

## Extending the app

The service architecture is designed to be pluggable. To add a new data source (e.g. Slack):

1. Add a `services/slack_service.py` that fetches the relevant data
2. Feed its output into `generate_brief()` in `ai_service.py`

That's it — the rest of the pipeline picks it up automatically.

---

## License

MIT
