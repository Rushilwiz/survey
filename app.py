"""Anonymous in-class survey app.

Two surfaces: a Typeform-style survey at `/` and a projector Counter at
`/counter`. Storage is a single SQLite file. We store no PII whatsoever -- only
a random Survey token (UUIDv4), answer slugs, an optional comment, and a UTC
timestamp. Dedup is best-effort via a short-lived cookie holding that token.
See PRD.md and docs/adr/0001-anonymity-and-best-effort-dedup.md.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import (
    Flask, g, jsonify, make_response, render_template, request, Response,
)

DB_PATH = os.environ.get("SURVEY_DB", "survey.db")
TOKEN_COOKIE = "survey_token"
COOKIE_MAX_AGE = 2 * 60 * 60  # ~2 hours
EXPORT_TOKEN = os.environ.get("EXPORT_TOKEN")  # if set, /export requires ?token=

PNA = "pna"  # "Prefer not to answer" slug, shared across questions

# Survey definition. `key` -> column; each option is (slug, label). The order
# here is the order shown. `multi` marks the one select-all question (q4).
QUESTIONS = [
    {"key": "q1", "multi": False,
     "text": "What year are you?",
     "options": [("first", "1st"), ("second", "2nd"), ("third", "3rd"),
                 ("fourth", "4th"), ("other", "Other"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q2", "multi": False,
     "text": "Are you a philosophy major?",
     "options": [("yes", "Yes"), ("no", "No"),
                 ("minor", "Minor or considering"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q3", "multi": False,
     "text": "Did you use any AI tool during the Groundwork reading?",
     "options": [("yes", "Yes"), ("no", "No"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q4", "multi": True,
     "text": "What did you use it for? (select all that apply)",
     "options": [("summarizing", "Summarizing instead of reading"),
                 ("explaining", "Explaining passages I didn't understand"),
                 ("answering", "Answering questions while reading"),
                 ("notes", "Generating study notes after reading"),
                 ("checking", "Checking my interpretation"),
                 ("other", "Other"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q5", "multi": False,
     "text": "How much of the 50 pages did you read in full yourself?",
     "options": [("none", "None"), ("quarter", "~A quarter"),
                 ("half", "~Half"), ("most", "Most"), ("all", "All"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q6", "multi": False,
     "text": "Did you read the primary text, an AI summary, or both?",
     "options": [("primary", "Primary only"), ("summary", "Summary only"),
                 ("both", "Both"), ("neither", "Neither"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q7", "multi": False,
     "text": "Did you watch the full episode?",
     "options": [("yes", "Yes"), ("skimmed", "Skimmed or partial"),
                 ("summary", "Read a summary instead"),
                 ("missed", "Didn't get to it"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q8", "multi": False,
     "text": "Did you use AI for anything related to the episode?",
     "options": [("no", "No"), ("summary", "Summary"),
                 ("discussion", "Discussion of themes"), ("other", "Other"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q9", "multi": False,
     "text": "Was your AI use more to replace effort or support effort?",
     "options": [("replace", "Mostly replace"), ("support", "Mostly support"),
                 ("mix", "Mix"), ("none", "Didn't use"),
                 (PNA, "Prefer not to answer")]},
    {"key": "q10", "multi": False,
     "text": "Did your AI use feel consistent with the course policy?",
     "options": [("yes", "Yes"), ("no", "No"),
                 ("unsure", "Wasn't sure what the policy was"),
                 ("none", "Didn't use AI"),
                 (PNA, "Prefer not to answer")]},
]
Q_KEYS = [q["key"] for q in QUESTIONS]
ALLOWED = {q["key"]: {slug for slug, _ in q["options"]} for q in QUESTIONS}

app = Flask(__name__)


# --- database helpers -------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(app.root_path, "schema.sql")) as f:
        db.executescript(f.read())
    db.close()


def get_meta(key, default=None):
    row = get_db().execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key, value):
    db = get_db()
    db.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    db.commit()


def count_submissions():
    return get_db().execute("SELECT COUNT(*) AS n FROM submissions").fetchone()["n"]


# --- validation -------------------------------------------------------------

def clean_answers(form):
    """Coerce a submitted form into stored slugs.

    Single-choice: an invalid or missing value becomes PNA (an unanswered
    single question is a deliberate "prefer not to answer"). Multi-select (q4):
    keep the subset of valid slugs; an empty selection stays empty (means "no
    purposes / didn't use AI", distinct from a deliberate PNA); if PNA is
    present it is mutually exclusive and wins.
    """
    answers = {}
    for q in QUESTIONS:
        key = q["key"]
        if q["multi"]:
            picked = [v for v in form.getlist(key) if v in ALLOWED[key]]
            if PNA in picked:
                picked = [PNA]
            answers[key] = ",".join(dict.fromkeys(picked))  # dedupe, keep order
        else:
            val = form.get(key, "")
            answers[key] = val if val in ALLOWED[key] else PNA
    comments = (form.get("comments") or "").strip()
    answers["comments"] = comments[:5000]  # cap; still no PII expectation
    return answers


# --- routes -----------------------------------------------------------------

@app.get("/")
def survey():
    token = request.cookies.get(TOKEN_COOKIE) or str(uuid.uuid4())
    resp = make_response(render_template("survey.html", questions=QUESTIONS))
    resp.set_cookie(
        TOKEN_COOKIE, token, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="Lax",
    )
    return resp


@app.post("/submit")
def submit():
    # Server owns the token: reuse the cookie, mint one if somehow absent.
    token = request.cookies.get(TOKEN_COOKIE) or str(uuid.uuid4())
    is_htmx = request.headers.get("HX-Request") == "true"

    answers = clean_answers(request.form)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO submissions "
            "(uuid, q1,q2,q3,q4,q5,q6,q7,q8,q9,q10, comments, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [token] + [answers[k] for k in Q_KEYS]
            + [answers["comments"], datetime.now(timezone.utc).isoformat()],
        )
        db.commit()
        already = False
    except sqlite3.IntegrityError:
        already = True  # this token already submitted

    status = 409 if already else 200
    stem = "already" if already else "success"
    template = f"_{stem}.html" if is_htmx else f"{stem}.html"
    resp = make_response(render_template(template), status)
    resp.set_cookie(
        TOKEN_COOKIE, token, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="Lax",
    )
    return resp


@app.get("/counter")
def counter():
    class_size = get_meta("class_size")
    return render_template(
        "counter.html", count=count_submissions(), class_size=class_size
    )


@app.get("/count")
def count():
    cs = get_meta("class_size")
    return jsonify(count=count_submissions(),
                   class_size=int(cs) if cs and cs.isdigit() else None)


@app.post("/class_size")
def class_size():
    raw = (request.form.get("class_size") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        set_meta("class_size", int(raw))
    return jsonify(count=count_submissions(),
                   class_size=int(raw) if raw.isdigit() else None)


@app.get("/export")
def export():
    if EXPORT_TOKEN and request.args.get("token") != EXPORT_TOKEN:
        return Response("forbidden", status=403, mimetype="text/plain")
    import csv
    import io
    cols = ["id", "uuid"] + Q_KEYS + ["comments", "created_at"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for row in get_db().execute(
        f"SELECT {','.join(cols)} FROM submissions ORDER BY id"
    ):
        w.writerow([row[c] for c in cols])
    return Response(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=survey.csv"},
    )


# Ensure the schema exists on import (safe: CREATE TABLE IF NOT EXISTS).
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
