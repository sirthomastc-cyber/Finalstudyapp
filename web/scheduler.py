"""
scheduler.py — Adaptive daily study schedule (spec section 4).

Deliberately algorithmic rather than AI-driven: it needs to run instantly,
offline, every time the dashboard opens, and the spec's requirement is
that it "dynamically calculates" priority from exam proximity, mastery,
and consistency — none of which need a language model, just arithmetic
over data already in the database.
"""

import time
from datetime import datetime

import mastery as mastery_engine

DAY = 86400


def _days_to_next_exam(conn, subject):
    row = conn.execute(
        "SELECT exam_date FROM exams WHERE subject_name = ? ORDER BY exam_date ASC LIMIT 1",
        (subject,),
    ).fetchone()
    if not row:
        return None
    try:
        exam_date = datetime.strptime(row["exam_date"], "%Y-%m-%d")
    except ValueError:
        return None
    delta = (exam_date - datetime.now()).days
    return max(0, delta)


def _days_since_last_session(conn, subject):
    row = conn.execute(
        "SELECT MAX(started_at) AS last FROM sessions WHERE subject_name = ?",
        (subject,),
    ).fetchone()
    if not row or not row["last"]:
        return 14  # never studied — treat as very stale
    return max(0, (int(time.time()) - row["last"]) / DAY)


def priority_for_subject(conn, subject):
    mastery, confidence, _ = mastery_engine.subject_mastery(conn, subject)
    days_to_exam = _days_to_next_exam(conn, subject)
    staleness = _days_since_last_session(conn, subject)

    exam_urgency = 100 - min(100, (days_to_exam or 60) / 60 * 100) if days_to_exam is not None else 20
    weakness = 100 - mastery
    staleness_score = min(100, staleness / 7 * 100)

    score = round(0.4 * exam_urgency + 0.4 * weakness + 0.2 * staleness_score)
    return {
        "subject": subject,
        "priority_score": score,
        "mastery": mastery,
        "days_to_exam": days_to_exam,
        "days_since_last_session": round(staleness, 1),
    }


def todays_schedule(conn, total_minutes=180):
    subjects = [r["name"] for r in conn.execute("SELECT name FROM subjects").fetchall()]
    if not subjects:
        return {"mission": None, "allocations": []}

    priorities = [priority_for_subject(conn, s) for s in subjects]
    priorities.sort(key=lambda p: p["priority_score"], reverse=True)

    total_score = sum(p["priority_score"] for p in priorities) or 1
    allocations = []
    for p in priorities:
        minutes = round(total_minutes * p["priority_score"] / total_score)
        allocations.append({**p, "suggested_minutes": minutes})

    top = priorities[0]
    breakdown = mastery_engine.topic_breakdown(conn, top["subject"])
    if breakdown:
        weakest_topic = min(breakdown, key=breakdown.get)
    else:
        weakest_topic = "General revision"

    mission = {
        "subject": top["subject"],
        "topic": weakest_topic,
        "reason": _explain(top),
    }

    return {"mission": mission, "allocations": allocations}


def _explain(p):
    reasons = []
    if p["days_to_exam"] is not None and p["days_to_exam"] <= 30:
        reasons.append(f"exam in {p['days_to_exam']} days")
    if p["mastery"] < 60:
        reasons.append(f"mastery is only {p['mastery']}%")
    if p["days_since_last_session"] >= 3:
        reasons.append(f"not studied in {round(p['days_since_last_session'])} days")
    if not reasons:
        reasons.append("keeping this subject on track")
    return ", ".join(reasons)
