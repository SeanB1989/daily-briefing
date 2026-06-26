import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "chief.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Items captured via the dump box
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'inbox',   -- inbox | scheduled | done | deleted | someday
            category TEXT,                 -- task | event | idea | reference | delegate
            ai_suggestion TEXT,            -- what the AI thinks you should do with it
            ai_reasoning TEXT,             -- why
            user_decision TEXT,            -- what you actually decided
            notes TEXT
        )
    """)

    # Daily briefs generated each morning
    c.execute("""
        CREATE TABLE IF NOT EXISTS briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            raw_context TEXT,              -- JSON snapshot of emails + calendar fed to AI
            brief_text TEXT,               -- the AI's written summary
            proposed_priorities TEXT,      -- JSON list of up to 3 priorities with reasoning
            confirmed_priorities TEXT,     -- JSON list after user confirms/edits
            confirmed_at TEXT
        )
    """)

    # Google OAuth tokens (single-user app)
    c.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY,
            token TEXT,
            refresh_token TEXT,
            token_uri TEXT,
            client_id TEXT,
            client_secret TEXT,
            scopes TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# ── Items ────────────────────────────────────────────────────────────────────

def add_item(content: str) -> int:
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO items (content, created_at) VALUES (?, ?)",
        (content.strip(), now)
    )
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_inbox_items():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM items WHERE status = 'inbox' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_item(item_id: int, **kwargs):
    conn = get_db()
    c = conn.cursor()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [item_id]
    c.execute(f"UPDATE items SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()


# ── Briefs ───────────────────────────────────────────────────────────────────

def get_or_create_brief(date_str: str) -> dict:
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM briefs WHERE date = ?", (date_str,)).fetchone()
    if not row:
        c.execute("INSERT INTO briefs (date) VALUES (?)", (date_str,))
        conn.commit()
        row = c.execute("SELECT * FROM briefs WHERE date = ?", (date_str,)).fetchone()
    conn.close()
    return dict(row)


def update_brief(date_str: str, **kwargs):
    conn = get_db()
    c = conn.cursor()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [date_str]
    c.execute(f"UPDATE briefs SET {fields} WHERE date = ?", values)
    conn.commit()
    conn.close()


# ── OAuth tokens ─────────────────────────────────────────────────────────────

def save_tokens(creds):
    import json
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("DELETE FROM oauth_tokens")
    c.execute("""
        INSERT INTO oauth_tokens
            (id, token, refresh_token, token_uri, client_id, client_secret, scopes, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
    """, (
        creds.token,
        creds.refresh_token,
        creds.token_uri,
        creds.client_id,
        creds.client_secret,
        json.dumps(list(creds.scopes)),
        now
    ))
    conn.commit()
    conn.close()


def load_tokens():
    import json
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM oauth_tokens WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)
