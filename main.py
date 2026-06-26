import os
import json
from datetime import datetime, timezone
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

from database import (
    init_db, add_item, get_inbox_items, update_item,
    get_or_create_brief, update_brief, save_tokens, load_tokens
)
from services.gmail_service import get_important_emails
from services.calendar_service import get_todays_events, get_upcoming_events
from services.ai_service import generate_brief, triage_items
from services.jobs_service import get_linkedin_jobs, get_recruiter_emails

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

# Allow OAuth over HTTP on Replit (Replit handles HTTPS termination)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Google OAuth scopes we need
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_credentials() -> Credentials | None:
    """Load stored OAuth credentials and refresh if needed."""
    token_data = load_tokens()
    if not token_data:
        return None

    import json as _json
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=_json.loads(token_data["scopes"]),
    )

    # Refresh the access token if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(google.auth.transport.requests.Request())
            save_tokens(creds)
        except Exception:
            return None

    return creds


def build_oauth_flow():
    """Build the Google OAuth flow using client secrets from env vars."""
    client_config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ["OAUTH_REDIRECT_URI"]],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.environ["OAUTH_REDIRECT_URI"],
    )
    return flow


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def today_display() -> str:
    return datetime.now(timezone.utc).strftime("%A, %d %B %Y")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))
    return redirect(url_for("brief"))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/connect-google")
def connect_google():
    flow = build_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    flow = build_oauth_flow()
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    save_tokens(creds)
    flash("Google account connected. You're all set.", "success")
    return redirect(url_for("brief"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Brief ─────────────────────────────────────────────────────────────────────

@app.route("/brief")
def brief():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    date = today_str()
    brief_record = get_or_create_brief(date)
    inbox_count = len(get_inbox_items())

    # Parse confirmed priorities if they exist
    confirmed = []
    if brief_record.get("confirmed_priorities"):
        try:
            confirmed = json.loads(brief_record["confirmed_priorities"])
        except Exception:
            pass

    # Parse proposed priorities if they exist
    proposed = []
    if brief_record.get("proposed_priorities"):
        try:
            proposed = json.loads(brief_record["proposed_priorities"])
        except Exception:
            pass

    return render_template(
        "brief.html",
        date_display=today_display(),
        brief=brief_record,
        proposed=proposed,
        confirmed=confirmed,
        inbox_count=inbox_count,
    )


@app.route("/api/generate-brief", methods=["POST"])
def api_generate_brief():
    """Called via AJAX when user clicks 'Generate my brief'."""
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        emails = get_important_emails(creds)
        events = get_todays_events(creds)
        upcoming = get_upcoming_events(creds)
        inbox_items = get_inbox_items()
        recruiter_emails = get_recruiter_emails(creds)
        linkedin_jobs = get_linkedin_jobs()

        brief_data = generate_brief(emails, events, upcoming, inbox_items, recruiter_emails, linkedin_jobs)

        # Save to DB
        date = today_str()
        context_snapshot = json.dumps({
            "emails": emails,
            "events": events,
            "upcoming": upcoming,
            "inbox_items": inbox_items,
        })
        update_brief(
            date,
            raw_context=context_snapshot,
            brief_text=brief_data.get("summary", ""),
            proposed_priorities=json.dumps(brief_data.get("priorities", [])),
        )

        return jsonify(brief_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/confirm-priorities", methods=["POST"])
def api_confirm_priorities():
    """User has reviewed and confirmed (or edited) their top 3 priorities."""
    data = request.get_json()
    priorities = data.get("priorities", [])
    date = today_str()
    update_brief(
        date,
        confirmed_priorities=json.dumps(priorities),
        confirmed_at=datetime.now(timezone.utc).isoformat(),
    )
    return jsonify({"ok": True})


# ── Dump ──────────────────────────────────────────────────────────────────────

@app.route("/dump", methods=["GET", "POST"])
def dump():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            # Support multi-line dumps — each non-empty line becomes its own item
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            for line in lines:
                add_item(line)
            flash(f"{len(lines)} item{'s' if len(lines) != 1 else ''} added to your inbox.", "success")
        return redirect(url_for("dump"))

    inbox_items = get_inbox_items()
    inbox_count = len(inbox_items)
    return render_template("dump.html", inbox_count=inbox_count)


@app.route("/api/dump-quick", methods=["POST"])
def api_dump_quick():
    """AJAX endpoint for quick-add from any page."""
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Empty content"}), 400

    item_id = add_item(content)
    return jsonify({"ok": True, "id": item_id})


# ── Triage ────────────────────────────────────────────────────────────────────

@app.route("/triage")
def triage():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    inbox_items = get_inbox_items()
    inbox_count = len(inbox_items)
    return render_template("triage.html", items=inbox_items, inbox_count=inbox_count)


@app.route("/api/triage-ai", methods=["POST"])
def api_triage_ai():
    """Ask AI to suggest categories/actions for all inbox items."""
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Not authenticated"}), 401

    items = get_inbox_items()
    if not items:
        return jsonify({"items": []})

    enriched = triage_items(items)
    return jsonify({"items": enriched})


@app.route("/api/triage-item", methods=["POST"])
def api_triage_item():
    """User has made a decision on one item."""
    data = request.get_json()
    item_id = data.get("id")
    decision = data.get("decision")  # do_now | schedule | someday | delegate | delete

    if not item_id or not decision:
        return jsonify({"error": "Missing id or decision"}), 400

    status_map = {
        "do_now": "inbox",       # stays in inbox, flagged as urgent
        "schedule": "scheduled",
        "someday": "someday",
        "delegate": "someday",   # could add a delegate field later
        "delete": "deleted",
    }

    update_item(item_id, status=status_map.get(decision, "inbox"), user_decision=decision)
    return jsonify({"ok": True})


# ── Boot ──────────────────────────────────────────────────────────────────────

# Initialise DB on startup (works with both gunicorn and direct python)
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
