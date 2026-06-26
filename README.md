# Chief of Staff

Your personal command centre. Dumps, briefs, priorities — no overwhelm.

Built with Python/Flask, Google APIs, and Claude.

---

## What it does

- **Dump** — capture anything from your head in seconds, from any page
- **Morning Brief** — AI reads your Gmail + Calendar + inbox and tells you what actually matters today, with reasoning
- **Triage** — process your inbox with AI suggestions; one decision per item

---

## Setup (do this once)

### 1. Create a Replit project

1. Go to [replit.com](https://replit.com) and create a new Repl
2. Choose **Python** as the language
3. Upload all these files into the Repl (or paste them in)

### 2. Set up Google Cloud (to get Gmail + Calendar access)

This is the fiddly bit but you only do it once.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project — call it "Chief of Staff" or whatever
3. In the left menu go to **APIs & Services → Library**
4. Search and enable:
   - **Gmail API**
   - **Google Calendar API**
   - **Google People API** (for your name/email)
5. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**
   - Fill in app name ("Chief of Staff"), your email, and save
   - Add scopes: `.../auth/gmail.readonly` and `.../auth/calendar.readonly`
   - Add yourself as a test user (your Gmail address)
6. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Name: "Chief of Staff"
   - Authorised redirect URI: `https://YOUR-REPL-URL.repl.co/oauth2callback`
     (you'll see your Repl URL once it's running — come back and add it here)
   - Click Create, then **download the credentials**

### 3. Add secrets to Replit

In your Repl, click the **Secrets** tab (padlock icon) and add:

| Key | Value |
|-----|-------|
| `GOOGLE_CLIENT_ID` | From your downloaded credentials JSON |
| `GOOGLE_CLIENT_SECRET` | From your downloaded credentials JSON |
| `OAUTH_REDIRECT_URI` | `https://YOUR-REPL-URL.repl.co/oauth2callback` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com) |
| `FLASK_SECRET_KEY` | Any random string — e.g. `my-secret-key-abc123` |

### 4. Install dependencies

In the Replit Shell, run:
```
pip install -r requirements.txt
```

### 5. Run it

Click the **Run** button, or in the shell:
```
python main.py
```

Visit your Repl URL, click **Connect Google Account**, and you're in.

---

## Day-to-day use

**Morning** — open the app, hit "Generate my brief". Read it. Confirm your top 3. You're done in under 5 minutes.

**Throughout the day** — any time something hits your brain, use the quick dump bar at the top. Don't think about where it goes, just dump it.

**Evening (or whenever)** — go to Triage, hit "Get AI suggestions", and burn through your inbox. Each item gets one decision: Do it now, Schedule, Someday, Delegate, or Delete.

---

## Adding Slack later

When you're employed again, you can hook in Slack by:
1. Installing `slack-sdk` in requirements.txt
2. Adding a `services/slack_service.py` that pulls DMs and mentions
3. Feeding the Slack data into the `generate_brief()` call in `ai_service.py`

The architecture is already set up for it.

---

## File structure

```
chief-of-staff/
├── main.py              # Flask routes
├── database.py          # SQLite schema + helpers
├── requirements.txt     # Python deps
├── services/
│   ├── gmail_service.py     # Gmail API
│   ├── calendar_service.py  # Google Calendar API
│   └── ai_service.py        # Claude (brief + triage)
└── templates/
    ├── base.html        # Nav, quick dump bar
    ├── login.html       # Google sign-in
    ├── brief.html       # Morning brief
    ├── dump.html        # Dump box
    └── triage.html      # Triage inbox
```
