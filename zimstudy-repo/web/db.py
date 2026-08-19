"""
db.py — SQLite schema and connection helper for ZIMStudy AI Web Edition.
Standard library only (sqlite3). Uses FTS5 for document search, which
ships built into Python's sqlite3 on modern builds.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "zimstudy.db")

os.makedirs(DATA_DIR, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT,
    school TEXT,
    grade TEXT,
    exam_board TEXT,
    exam_year TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_grade TEXT DEFAULT 'A',
    UNIQUE(name COLLATE NOCASE)
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL,
    paper_number TEXT,
    exam_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL,
    topic TEXT,
    started_at INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL,
    interruptions INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,      -- textbook, notes, past_paper, marking_scheme, transcript, worksheet
    subject TEXT,
    filename TEXT,
    uploaded_at INTEGER NOT NULL,
    full_text TEXT NOT NULL,
    page_count INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, full_text, content='documents', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, full_text) VALUES (new.id, new.title, new.full_text);
END;
CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, full_text) VALUES('delete', old.id, old.title, old.full_text);
END;
CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, full_text) VALUES('delete', old.id, old.title, old.full_text);
    INSERT INTO documents_fts(rowid, title, full_text) VALUES (new.id, new.title, new.full_text);
END;

CREATE TABLE IF NOT EXISTS weekly_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    source_document_id INTEGER,
    target_mastery INTEGER DEFAULT 90,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    question_type TEXT DEFAULT 'short_answer',
    difficulty INTEGER DEFAULT 2,
    source TEXT DEFAULT 'manual',   -- manual or ai
    created_at INTEGER NOT NULL,
    ease REAL DEFAULT 2.5,
    interval_days REAL DEFAULT 1,
    due_at INTEGER NOT NULL,
    times_seen INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_item_id INTEGER,
    subject TEXT,
    topic TEXT,
    correct INTEGER,
    answered_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS focus_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,   -- session_start, session_end, pause, resume, interruption
    at INTEGER NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS ai_chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    topic TEXT,
    role TEXT NOT NULL,   -- user or assistant
    content TEXT NOT NULL,
    at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS examiner_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT,
    difficulty INTEGER DEFAULT 2,
    question_count INTEGER NOT NULL,
    marks INTEGER NOT NULL,
    total_marks INTEGER NOT NULL,
    percentage INTEGER NOT NULL,
    weak_areas TEXT DEFAULT '',
    feedback TEXT DEFAULT '',
    taken_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
