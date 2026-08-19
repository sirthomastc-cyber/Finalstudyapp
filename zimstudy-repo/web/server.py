#!/usr/bin/env python3
"""
ZIMStudy AI — Web Edition, full backend.

Standard library only for the core app (http.server, sqlite3, urllib for
AI calls). PDF/DOCX upload uses optional pypdf/python-docx and degrades
gracefully if they aren't installed — see documents.py.

Run:
    python3 server.py
Optional AI Teacher / Examiner (off by default — see ai_provider.py):
    export ANTHROPIC_API_KEY=sk-...
    python3 server.py
"""

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import ai_provider
import documents as doc_engine
import mastery as mastery_engine
import scheduler
from db import get_db, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

ROUTES = {"GET": [], "POST": [], "DELETE": []}


def route(method, pattern):
    compiled = re.compile("^" + pattern + "$")

    def decorator(fn):
        ROUTES[method].append((compiled, fn))
        return fn

    return decorator


def now():
    return int(time.time())


# ---------------------------------------------------------------- profile

@route("GET", r"/api/profile")
def get_profile(ctx):
    conn = get_db()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


@route("POST", r"/api/profile")
def save_profile(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        """
        INSERT INTO profile (id, name, school, grade, exam_board, exam_year)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, school=excluded.school, grade=excluded.grade,
            exam_board=excluded.exam_board, exam_year=excluded.exam_year
        """,
        (d.get("name", ""), d.get("school", ""), d.get("grade", ""),
         d.get("exam_board", ""), d.get("exam_year", "")),
    )
    conn.commit(); conn.close()
    return {"ok": True}


# ---------------------------------------------------------------- subjects

@route("GET", r"/api/subjects")
def list_subjects(ctx):
    conn = get_db()
    rows = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/subjects")
def add_subject(ctx):
    import sqlite3
    name = ctx["body"].get("name", "").strip()
    if not name:
        return {"error": "name required"}, 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO subjects (name, target_grade) VALUES (?, ?)",
            (name, ctx["body"].get("target_grade", "A")),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": f"'{name}' is already in your subject list"}, 400
    conn.close()
    return {"ok": True}


@route("DELETE", r"/api/subjects/(\d+)")
def delete_subject(ctx):
    conn = get_db()
    conn.execute("DELETE FROM subjects WHERE id = ?", (ctx["match"][0],))
    conn.commit(); conn.close()
    return {"ok": True}


# ------------------------------------------------------------------ exams

@route("GET", r"/api/exams")
def list_exams(ctx):
    conn = get_db()
    rows = conn.execute("SELECT * FROM exams ORDER BY exam_date").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/exams")
def add_exam(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        "INSERT INTO exams (subject_name, paper_number, exam_date) VALUES (?, ?, ?)",
        (d.get("subject_name", ""), d.get("paper_number", ""), d.get("exam_date", "")),
    )
    conn.commit(); conn.close()
    return {"ok": True}


@route("DELETE", r"/api/exams/(\d+)")
def delete_exam(ctx):
    conn = get_db()
    conn.execute("DELETE FROM exams WHERE id = ?", (ctx["match"][0],))
    conn.commit(); conn.close()
    return {"ok": True}


# --------------------------------------------------------------- sessions

@route("GET", r"/api/sessions")
def list_sessions(ctx):
    conn = get_db()
    rows = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT 100").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/sessions")
def add_session(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (subject_name, topic, started_at, duration_minutes, interruptions) "
        "VALUES (?, ?, ?, ?, ?)",
        (d.get("subject_name", ""), d.get("topic", ""), now(),
         int(d.get("duration_minutes", 0)), int(d.get("interruptions", 0))),
    )
    conn.commit(); conn.close()
    return {"ok": True}


# -------------------------------------------------------------- documents

@route("GET", r"/api/documents")
def list_documents(ctx):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, doc_type, subject, filename, uploaded_at, page_count FROM documents "
        "ORDER BY uploaded_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("GET", r"/api/documents/(\d+)")
def get_document(ctx):
    conn = get_db()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (ctx["match"][0],)).fetchone()
    conn.close()
    if not row:
        return {"error": "not found"}, 404
    d = dict(row)
    if len(d["full_text"]) > 20000:
        d["full_text"] = d["full_text"][:20000] + "\n...(truncated for display)"
    return d


@route("DELETE", r"/api/documents/(\d+)")
def delete_document(ctx):
    conn = get_db()
    conn.execute("DELETE FROM documents WHERE id = ?", (ctx["match"][0],))
    conn.commit(); conn.close()
    return {"ok": True}


@route("POST", r"/api/documents")
def upload_document(ctx):
    d = ctx["body"]
    title = d.get("title", "").strip() or d.get("filename", "Untitled")
    doc_type = d.get("doc_type", "notes")
    subject = d.get("subject", "")

    if "content_b64" in d and d.get("filename"):
        try:
            text, pages = doc_engine.extract_text(d["filename"], d["content_b64"])
        except doc_engine.ExtractionError as e:
            return {"error": str(e)}, 400
    elif "text" in d:
        text, pages = d["text"], 1
    else:
        return {"error": "provide either content_b64+filename or text"}, 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO documents (title, doc_type, subject, filename, uploaded_at, full_text, page_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, doc_type, subject, d.get("filename", ""), now(), text, pages),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": doc_id, "extracted_chars": len(text), "pages": pages}


@route("GET", r"/api/documents/search")
def search_documents(ctx):
    q = ctx["query"].get("q", [""])[0]
    subject = ctx["query"].get("subject", [None])[0]
    conn = get_db()
    results = doc_engine.search(conn, q, subject=subject)
    conn.close()
    return results


# ------------------------------------------------------------ weekly goals

@route("GET", r"/api/weekly-goals")
def list_weekly_goals(ctx):
    conn = get_db()
    rows = conn.execute("SELECT * FROM weekly_goals ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/weekly-goals")
def add_weekly_goal(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        "INSERT INTO weekly_goals (week_number, subject, topic, source_document_id, target_mastery, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (d.get("week_number"), d.get("subject", ""), d.get("topic", ""),
         d.get("source_document_id"), d.get("target_mastery", 90), now()),
    )
    conn.commit(); conn.close()
    return {"ok": True}


@route("DELETE", r"/api/weekly-goals/(\d+)")
def delete_weekly_goal(ctx):
    conn = get_db()
    conn.execute("DELETE FROM weekly_goals WHERE id = ?", (ctx["match"][0],))
    conn.commit(); conn.close()
    return {"ok": True}


# ------------------------------------------------------------- quiz items

@route("GET", r"/api/quiz-items")
def list_quiz_items(ctx):
    subject = ctx["query"].get("subject", [None])[0]
    conn = get_db()
    if subject:
        rows = conn.execute(
            "SELECT * FROM quiz_items WHERE subject = ? ORDER BY created_at DESC", (subject,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM quiz_items ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/quiz-items")
def add_quiz_item(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        "INSERT INTO quiz_items (subject, topic, question, answer, question_type, difficulty, "
        "source, created_at, due_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (d.get("subject", ""), d.get("topic", ""), d.get("question", ""), d.get("answer", ""),
         d.get("question_type", "short_answer"), int(d.get("difficulty", 2)),
         d.get("source", "manual"), now(), now()),
    )
    conn.commit(); conn.close()
    return {"ok": True}


@route("DELETE", r"/api/quiz-items/(\d+)")
def delete_quiz_item(ctx):
    conn = get_db()
    conn.execute("DELETE FROM quiz_items WHERE id = ?", (ctx["match"][0],))
    conn.commit(); conn.close()
    return {"ok": True}


@route("GET", r"/api/quiz-items/next")
def next_quiz_items(ctx):
    subject = ctx["query"].get("subject", [None])[0]
    count = int(ctx["query"].get("count", [5])[0])
    conn = get_db()

    base_where = ["subject = ?"] if subject else []
    base_params = [subject] if subject else []

    due_where = base_where + ["due_at <= ?"]
    due_sql = "SELECT * FROM quiz_items WHERE " + " AND ".join(due_where) + " ORDER BY due_at ASC LIMIT ?"
    due = conn.execute(due_sql, base_params + [now(), count]).fetchall()

    remaining = count - len(due)
    fresh = []
    if remaining > 0:
        exclude_ids = [r["id"] for r in due]
        fresh_where = base_where + ["times_seen = 0"]
        fresh_params = list(base_params)
        if exclude_ids:
            placeholders = ",".join("?" * len(exclude_ids))
            fresh_where.append(f"id NOT IN ({placeholders})")
            fresh_params += exclude_ids
        fresh_sql = "SELECT * FROM quiz_items WHERE " + " AND ".join(fresh_where) + " ORDER BY RANDOM() LIMIT ?"
        fresh = conn.execute(fresh_sql, fresh_params + [remaining]).fetchall()

    conn.close()
    return [dict(r) for r in list(due) + list(fresh)]


@route("POST", r"/api/quiz-attempts")
def record_quiz_attempt(ctx):
    d = ctx["body"]
    quiz_item_id = d.get("quiz_item_id")
    correct = 1 if d.get("correct") else 0

    conn = get_db()
    item = conn.execute("SELECT * FROM quiz_items WHERE id = ?", (quiz_item_id,)).fetchone()
    if not item:
        conn.close()
        return {"error": "quiz item not found"}, 404

    conn.execute(
        "INSERT INTO quiz_attempts (quiz_item_id, subject, topic, correct, answered_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (quiz_item_id, item["subject"], item["topic"], correct, now()),
    )

    ease = item["ease"]
    interval = item["interval_days"]
    if correct:
        interval = max(1, interval * ease)
        ease = min(2.8, ease + 0.1)
    else:
        interval = 1
        ease = max(1.3, ease - 0.2)

    conn.execute(
        "UPDATE quiz_items SET ease = ?, interval_days = ?, due_at = ?, "
        "times_seen = times_seen + 1, times_correct = times_correct + ? WHERE id = ?",
        (ease, interval, now() + int(interval * 86400), correct, quiz_item_id),
    )
    conn.commit(); conn.close()
    return {"ok": True}


# ---------------------------------------------------------- formal examiner

@route("GET", r"/api/examiner/results")
def examiner_results(ctx):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM examiner_results ORDER BY taken_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@route("POST", r"/api/ai/generate-exam")
def ai_generate_exam(ctx):
    d = ctx["body"]
    subject = d.get("subject", "").strip()
    topic = d.get("topic", "").strip()
    difficulty = max(1, min(5, int(d.get("difficulty", 2))))
    count = max(3, min(30, int(d.get("count", 10))))
    if not subject or not topic:
        return {"error": "subject and topic are required"}, 400
    conn = get_db()
    excerpts = None
    if d.get("use_documents"):
        results = doc_engine.search(conn, topic, subject=subject)
        excerpts = [r["excerpt"] for r in results] if results else None
    try:
        items = ai_provider.generate_exam(subject, topic, difficulty, count, excerpts)
    except ai_provider.AIUnavailable as e:
        conn.close()
        return {"error": "AI Examiner is temporarily offline.", "detail": str(e)}, 503
    # Normalize provider output so the client has a stable contract.
    normalized = []
    for item in items[:count]:
        if not isinstance(item, dict) or not item.get("question"):
            continue
        options = item.get("options") or []
        if not options:
            options = [item.get("answer", "")]
        normalized.append({
            "question": str(item["question"]),
            "options": [str(o) for o in options],
            "answer": str(item.get("answer", options[0])),
            "explanation": str(item.get("explanation", "")),
            "topic": str(item.get("topic", topic)),
            "marks": int(item.get("marks", 1)),
        })
    conn.close()
    if not normalized:
        return {"error": "The AI returned no usable questions. Try again."}, 502
    return {"subject": subject, "topic": topic, "difficulty": difficulty, "questions": normalized}


@route("POST", r"/api/examiner/results")
def save_examiner_result(ctx):
    d = ctx["body"]
    questions = d.get("questions") or []
    answers = d.get("answers") or []
    if not questions:
        return {"error": "questions are required"}, 400
    marks = 0
    weak = []
    for index, question in enumerate(questions):
        expected = str(question.get("answer", "")).strip().lower()
        actual = str(answers[index] if index < len(answers) else "").strip().lower()
        if actual and actual == expected:
            marks += int(question.get("marks", 1))
        else:
            weak.append(question.get("topic") or d.get("topic", "Review"))
    total = sum(int(q.get("marks", 1)) for q in questions)
    percentage = round(100 * marks / total) if total else 0
    weak = list(dict.fromkeys(weak))
    feedback = (
        "Strong formal assessment. Keep revising with timed practice."
        if percentage >= 80 else
        "Review the weak areas, ask the Teacher to explain them, then retake the assessment."
    )
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO examiner_results "
        "(subject, topic, difficulty, question_count, marks, total_marks, percentage, weak_areas, feedback, taken_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (d.get("subject", ""), d.get("topic", ""), int(d.get("difficulty", 2)),
         len(questions), marks, total, percentage, json.dumps(weak), feedback, now()),
    )
    conn.commit(); conn.close()
    return {"ok": True, "id": cur.lastrowid, "marks": marks, "total_marks": total,
            "percentage": percentage, "weak_areas": weak, "feedback": feedback}


# --------------------------------------------------------- mastery/forecast

@route("GET", r"/api/mastery")
def get_all_mastery(ctx):
    conn = get_db()
    subjects = [r["name"] for r in conn.execute("SELECT name FROM subjects").fetchall()]
    result = {}
    for s in subjects:
        mastery, confidence, evidence = mastery_engine.subject_mastery(conn, s)
        result[s] = {
            "estimated_mastery": mastery,
            "confidence": confidence,
            "evidence": evidence,
            "topic_breakdown": mastery_engine.topic_breakdown(conn, s),
        }
    conn.close()
    return result


@route("GET", r"/api/forecast")
def get_forecast(ctx):
    conn = get_db()
    subjects = [r["name"] for r in conn.execute("SELECT name FROM subjects").fetchall()]
    forecasts = [mastery_engine.forecast_for_subject(conn, s) for s in subjects]
    conn.close()

    tally = {}
    for f in forecasts:
        g = f["predicted_grade"]
        tally[g] = tally.get(g, 0) + 1

    return {"forecasts": forecasts, "tally": tally}


@route("GET", r"/api/study-quality")
def get_study_quality(ctx):
    days = int(ctx["query"].get("days", [7])[0])
    conn = get_db()
    result = mastery_engine.study_quality_score(conn, now() - days * 86400)
    conn.close()
    return result


@route("GET", r"/api/progress")
def progress_snapshot(ctx):
    conn = get_db()
    today_start = now() - 86400
    week_start = now() - 7 * 86400
    today = conn.execute(
        "SELECT COALESCE(SUM(duration_minutes),0) AS minutes, COUNT(*) AS sessions "
        "FROM sessions WHERE started_at >= ?", (today_start,)).fetchone()
    week = conn.execute(
        "SELECT COALESCE(SUM(duration_minutes),0) AS minutes, COUNT(*) AS sessions "
        "FROM sessions WHERE started_at >= ?", (week_start,)).fetchone()
    days = conn.execute(
        "SELECT DISTINCT date(started_at,'unixepoch') AS day FROM sessions ORDER BY day DESC"
    ).fetchall()
    streak = 0
    from datetime import date, timedelta
    expected = date.today()
    for row in days:
        day = date.fromisoformat(row["day"])
        if day == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif day < expected:
            break
    subjects = [r["name"] for r in conn.execute("SELECT name FROM subjects ORDER BY name").fetchall()]
    breakdown = []
    for subject in subjects:
        mastery, confidence, evidence = mastery_engine.subject_mastery(conn, subject)
        topics = mastery_engine.topic_breakdown(conn, subject)
        breakdown.append({"subject": subject, "mastery": mastery, "confidence": confidence,
                          "topics": topics, "evidence": evidence})
    weak = []
    for row in breakdown:
        for topic, score in row["topics"].items():
            if score < 70:
                weak.append({"subject": row["subject"], "topic": topic, "score": score})
    weak.sort(key=lambda x: x["score"])
    strong = []
    for row in breakdown:
        for topic, score in row["topics"].items():
            if score >= 80:
                strong.append({"subject": row["subject"], "topic": topic, "score": score})
    recent = conn.execute(
        "SELECT subject, topic, percentage, marks, total_marks, taken_at "
        "FROM examiner_results ORDER BY taken_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return {"today": dict(today), "week": dict(week), "streak": streak,
            "subjects": breakdown, "weak_areas": weak[:8], "strong_areas": strong[:8],
            "recent_exams": [dict(r) for r in recent]}


# -------------------------------------------------------------- scheduler

@route("GET", r"/api/schedule/today")
def get_schedule_today(ctx):
    minutes = int(ctx["query"].get("minutes", [180])[0])
    conn = get_db()
    result = scheduler.todays_schedule(conn, total_minutes=minutes)
    conn.close()
    return result


# -------------------------------------------------------------- AI Teacher

@route("GET", r"/api/ai/status")
def ai_status(ctx):
    provider, has_key = ai_provider.current_provider()
    return {"provider": provider, "configured": has_key}


@route("POST", r"/api/ai/chat")
def ai_chat(ctx):
    d = ctx["body"]
    subject = d.get("subject", "General")
    topic = d.get("topic", "")
    message = d.get("message", "")
    history = d.get("history", [])

    conn = get_db()
    excerpts = None
    if d.get("use_documents"):
        results = doc_engine.search(conn, f"{topic} {message}", subject=subject)
        if results:
            excerpts = [f"{r['title']}: {r['excerpt']}" for r in results]

    try:
        reply = ai_provider.teach(subject, topic, message, history, source_excerpts=excerpts)
    except ai_provider.AIUnavailable:
        conn.close()
        return {
            "error": "AI Teacher is temporarily offline.",
            "offline_alternatives": [
                "Offline notes", "Saved questions", "Flashcards",
                "Previous explanations", "Study timer", "Downloaded materials",
            ],
        }, 503

    conn.execute(
        "INSERT INTO ai_chat_log (subject, topic, role, content, at) VALUES (?, ?, 'user', ?, ?)",
        (subject, topic, message, now()),
    )
    conn.execute(
        "INSERT INTO ai_chat_log (subject, topic, role, content, at) VALUES (?, ?, 'assistant', ?, ?)",
        (subject, topic, reply, now()),
    )
    conn.commit(); conn.close()
    return {"reply": reply, "grounded_in_documents": bool(excerpts)}


@route("POST", r"/api/ai/generate-quiz")
def ai_generate_quiz(ctx):
    d = ctx["body"]
    subject = d.get("subject", "")
    topic = d.get("topic", "")
    difficulty = int(d.get("difficulty", 2))
    count = int(d.get("count", 5))

    conn = get_db()
    excerpts = None
    if d.get("use_documents"):
        results = doc_engine.search(conn, topic, subject=subject)
        if results:
            excerpts = [r["excerpt"] for r in results]

    try:
        items = ai_provider.generate_quiz(subject, topic, difficulty, count, source_excerpts=excerpts)
    except ai_provider.AIUnavailable as e:
        conn.close()
        return {
            "error": "AI Examiner is temporarily offline.",
            "detail": str(e),
            "offline_alternatives": ["Add questions manually", "Practice saved questions", "Review flashcards"],
        }, 503

    inserted = 0
    for item in items:
        conn.execute(
            "INSERT INTO quiz_items (subject, topic, question, answer, question_type, difficulty, "
            "source, created_at, due_at) VALUES (?, ?, ?, ?, ?, ?, 'ai', ?, ?)",
            (subject, topic, item.get("question", ""), item.get("answer", ""),
             item.get("question_type", "short_answer"), int(item.get("difficulty", difficulty)),
             now(), now()),
        )
        inserted += 1
    conn.commit(); conn.close()
    return {"ok": True, "inserted": inserted, "items": items}


# ------------------------------------------------------------- YouTube

@route("POST", r"/api/youtube/transcript")
def youtube_transcript(ctx):
    """
    No network access to fetch YouTube captions server-side and no YouTube
    Data API key configured, so this accepts a transcript the user pastes
    in (YouTube's own "Show transcript" button provides this) and processes
    it exactly like any uploaded document from then on.
    """
    d = ctx["body"]
    url = d.get("url", "")
    transcript_text = d.get("transcript_text", "").strip()
    subject = d.get("subject", "")

    if not transcript_text:
        return {"error": "transcript_text is required — paste the video's transcript"}, 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO documents (title, doc_type, subject, filename, uploaded_at, full_text, page_count) "
        "VALUES (?, 'transcript', ?, ?, ?, ?, 1)",
        (f"YouTube: {url}"[:200], subject, url, now(), transcript_text),
    )
    doc_id = cur.lastrowid
    conn.commit(); conn.close()
    return {"ok": True, "document_id": doc_id}


# --------------------------------------------------------------- focus mode

@route("POST", r"/api/focus-events")
def log_focus_event(ctx):
    d = ctx["body"]
    conn = get_db()
    conn.execute(
        "INSERT INTO focus_events (event_type, at, note) VALUES (?, ?, ?)",
        (d.get("event_type", ""), now(), d.get("note", "")),
    )
    conn.commit(); conn.close()
    return {"ok": True}


# -------------------------------------------------------------- weekly report

@route("GET", r"/api/weekly-report")
def weekly_report(ctx):
    conn = get_db()
    week_start = now() - 7 * 86400

    sessions = conn.execute(
        "SELECT SUM(duration_minutes) AS mins FROM sessions WHERE started_at >= ?", (week_start,)
    ).fetchone()
    total_minutes = sessions["mins"] or 0

    attempts = conn.execute(
        "SELECT correct FROM quiz_attempts WHERE answered_at >= ?", (week_start,)
    ).fetchall()
    accuracy = round(100 * sum(a["correct"] for a in attempts) / len(attempts)) if attempts else None

    subjects = [r["name"] for r in conn.execute("SELECT name FROM subjects").fetchall()]

    subject_rows = []
    for s in subjects:
        m, _, _ = mastery_engine.subject_mastery(conn, s)
        subject_rows.append({"subject": s, "mastery": m})

    quality = mastery_engine.study_quality_score(conn, week_start)

    conn.close()

    narrative = f"You logged {total_minutes // 60}h {total_minutes % 60}m of focused study this week. "
    if accuracy is not None:
        narrative += f"Quiz accuracy across all subjects was {accuracy}%. "
    if subject_rows:
        strongest = max(subject_rows, key=lambda r: r["mastery"])
        weakest = min(subject_rows, key=lambda r: r["mastery"])
        narrative += (
            f"{strongest['subject']} is your strongest subject right now at "
            f"{strongest['mastery']}% estimated mastery. "
        )
        if weakest["subject"] != strongest["subject"]:
            narrative += (
                f"{weakest['subject']} needs the most attention at {weakest['mastery']}% — "
                f"consider shifting some time toward it next week."
            )

    ai_narrative = None
    if ai_provider.is_configured():
        try:
            ai_narrative = ai_provider.chat(
                "You are the AI Teacher inside ZIMStudy AI, giving a warm, direct weekly "
                "review to a ZIMSEC student using the exact numbers provided. 3-4 sentences, "
                "conversational, not robotic.",
                [{"role": "user", "content": json.dumps({
                    "total_minutes": total_minutes, "accuracy": accuracy, "subjects": subject_rows,
                    "study_quality": quality["score"],
                })}],
            )
        except ai_provider.AIUnavailable:
            ai_narrative = None

    return {
        "total_minutes": total_minutes,
        "quiz_accuracy": accuracy,
        "subjects": subject_rows,
        "study_quality": quality,
        "narrative": ai_narrative or narrative,
        "narrative_source": "ai" if ai_narrative else "template",
    }


# --------------------------------------------------------------------------
# HTTP plumbing
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "not found"}, 404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt, *args):
        pass

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path

        if method == "GET" and path in ("/", "/index.html"):
            return self._send_file(os.path.join(HTML_DIR, "index.html"), MIME_TYPES[".html"])
        if method == "GET" and path in ("/style.css", "/app.js"):
            ext = os.path.splitext(path)[1]
            return self._send_file(os.path.join(HTML_DIR, path.lstrip("/")), MIME_TYPES[ext])

        for pattern, fn in ROUTES[method]:
            m = pattern.match(path)
            if m:
                ctx = {
                    "match": m.groups(),
                    "query": parse_qs(parsed.query),
                    "body": self._read_json_body() if method == "POST" else {},
                }
                try:
                    result = fn(ctx)
                except Exception as e:  # never fail silently — spec section 30
                    return self._send_json({"error": f"Internal error: {e}"}, 500)
                if isinstance(result, tuple):
                    payload, status = result
                    return self._send_json(payload, status)
                return self._send_json(result)

        self._send_json({"error": "not found"}, 404)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")


def main():
    init_db()
    port = int(os.environ.get("PORT", 5000))
    provider, has_key = ai_provider.current_provider()
    print(f"ZIMStudy AI running at http://localhost:{port}  (Ctrl+C to stop)")
    if has_key:
        print(f"AI Teacher: ON  (provider: {provider})")
    else:
        env_var = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        print(f"AI Teacher: OFFLINE  (set {env_var} to enable)")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
