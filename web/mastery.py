"""
mastery.py — Estimated Mastery engine, A/B/C/D grade forecast, and the
Study Quality score. Deliberately rule-based and transparent (per spec
section 12: "use a transparent calculation rather than claiming that the
percentage represents literal knowledge" and section 17: "the score
should be explainable"). No AI call needed for any of this.
"""

import time

SEVEN_DAYS = 7 * 86400
THIRTY_DAYS = 30 * 86400


def _quiz_accuracy(conn, subject, topic=None, limit=30):
    q = "SELECT correct FROM quiz_attempts WHERE subject = ?"
    params = [subject]
    if topic:
        q += " AND topic = ?"
        params.append(topic)
    q += " ORDER BY answered_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    if not rows:
        exam_q = "SELECT percentage FROM examiner_results WHERE subject = ?"
        exam_params = [subject]
        if topic:
            exam_q += " AND topic = ?"
            exam_params.append(topic)
        exam_q += " ORDER BY taken_at DESC LIMIT ?"
        exam_params.append(limit)
        exams = conn.execute(exam_q, exam_params).fetchall()
        if exams:
            return round(sum(r["percentage"] for r in exams) / len(exams)), len(exams)
        return None, 0
    correct = sum(r["correct"] for r in rows)
    return round(100 * correct / len(rows)), len(rows)


def _consistency_score(conn, subject):
    since = int(time.time()) - SEVEN_DAYS
    row = conn.execute(
        "SELECT COUNT(DISTINCT date(started_at, 'unixepoch')) AS days "
        "FROM sessions WHERE subject_name = ? AND started_at >= ?",
        (subject, since),
    ).fetchone()
    days = row["days"] if row else 0
    return min(100, round(100 * days / 5))  # 5 active days/week = full marks


def _retention_score(conn, subject):
    rows = conn.execute(
        "SELECT times_seen, times_correct FROM quiz_items "
        "WHERE subject = ? AND times_seen >= 2",
        (subject,),
    ).fetchall()
    if not rows:
        return None
    ratios = [r["times_correct"] / r["times_seen"] for r in rows]
    return round(100 * sum(ratios) / len(ratios))


def subject_mastery(conn, subject):
    """Returns (mastery_pct, confidence, evidence_dict) for one subject."""
    accuracy, n_attempts = _quiz_accuracy(conn, subject)
    consistency = _consistency_score(conn, subject)
    retention = _retention_score(conn, subject)

    if accuracy is None:
        return 0, "Low", {"reason": "No quiz attempts recorded yet for this subject."}

    parts = [(accuracy, 0.65)]
    parts.append((consistency, 0.20))
    if retention is not None:
        parts.append((retention, 0.15))
    else:
        # redistribute retention's weight onto accuracy if we have no retention data yet
        parts[0] = (accuracy, 0.80)

    mastery = round(sum(v * w for v, w in parts))
    mastery = max(0, min(100, mastery))

    if n_attempts >= 20:
        confidence = "High"
    elif n_attempts >= 8:
        confidence = "Medium"
    else:
        confidence = "Low"

    evidence = {
        "quiz_accuracy": accuracy,
        "attempts_considered": n_attempts,
        "consistency_last_7_days": consistency,
        "retention": retention,
    }
    return mastery, confidence, evidence


def topic_breakdown(conn, subject):
    """Per-topic mastery within a subject, using the same accuracy-based logic."""
    topics = [
        r["topic"]
        for r in conn.execute(
            "SELECT DISTINCT topic FROM quiz_items WHERE subject = ?", (subject,)
        ).fetchall()
    ]
    topics += [
        r["topic"] for r in conn.execute(
            "SELECT DISTINCT topic FROM examiner_results WHERE subject = ? AND topic IS NOT NULL AND topic != ?",
            (subject, "")
        ).fetchall()
    ]
    topics = list(dict.fromkeys(topics))
    breakdown = {}
    for topic in topics:
        accuracy, n = _quiz_accuracy(conn, subject, topic=topic, limit=30)
        breakdown[topic] = accuracy if accuracy is not None else 0
    return breakdown


def grade_for_mastery(mastery):
    if mastery >= 85:
        return "A"
    if mastery >= 70:
        return "B"
    if mastery >= 55:
        return "C"
    if mastery >= 40:
        return "D"
    return "Below target"


def forecast_for_subject(conn, subject):
    mastery, confidence, evidence = subject_mastery(conn, subject)
    grade = grade_for_mastery(mastery)

    breakdown = topic_breakdown(conn, subject)
    what_would_change = None
    if breakdown:
        weakest_topic = min(breakdown, key=breakdown.get)
        weakest_score = breakdown[weakest_topic]
        thresholds = [40, 55, 70, 85]
        next_threshold = next((t for t in thresholds if t > mastery), None)
        if next_threshold and weakest_score < 80:
            next_grade = grade_for_mastery(next_threshold)
            what_would_change = (
                f"Your {subject} forecast could move to {next_grade} if you bring "
                f"{weakest_topic} (currently {weakest_score}%) up to around 80% and "
                f"keep your overall accuracy above {next_threshold}%."
            )

    return {
        "subject": subject,
        "estimated_mastery": mastery,
        "predicted_grade": grade,
        "confidence": confidence,
        "evidence": evidence,
        "topic_breakdown": breakdown,
        "what_would_change_forecast": what_would_change,
    }


def study_quality_score(conn, since_ts):
    """Composite 0-100 score explained by its own components."""
    sessions = conn.execute(
        "SELECT duration_minutes, interruptions FROM sessions WHERE started_at >= ?",
        (since_ts,),
    ).fetchall()
    total_minutes = sum(s["duration_minutes"] for s in sessions)
    total_interruptions = sum(s["interruptions"] for s in sessions)

    attempts = conn.execute(
        "SELECT correct FROM quiz_attempts WHERE answered_at >= ?", (since_ts,)
    ).fetchall()
    accuracy = (
        round(100 * sum(a["correct"] for a in attempts) / len(attempts))
        if attempts
        else None
    )

    focus_component = max(0, 100 - total_interruptions * 5)
    volume_component = min(100, round(100 * total_minutes / 600))  # 10h/week = full marks
    accuracy_component = accuracy if accuracy is not None else 50  # neutral if no data

    score = round(0.4 * accuracy_component + 0.35 * volume_component + 0.25 * focus_component)
    score = max(0, min(100, score))

    return {
        "score": score,
        "components": {
            "accuracy": accuracy_component,
            "study_volume": volume_component,
            "focus": focus_component,
        },
        "raw": {
            "total_minutes": total_minutes,
            "total_interruptions": total_interruptions,
            "quiz_attempts": len(attempts),
        },
    }
