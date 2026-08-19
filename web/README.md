# ZIMStudy AI — Web Edition

The Phase 1-6 feature set from the spec, running as a browser app with
a Python backend. No pip install required for the core app — only
`pypdf` / `python-docx` are needed if you want PDF/DOCX upload, and
those degrade gracefully (with a clear message) if missing.

## Run it

```
cd web
python3 server.py
```

Open **http://localhost:5000**. Data lives in `web/data/zimstudy.db`
(SQLite), created automatically.

## Turn on the AI Teacher / Examiner

Off by default — runs fully functional without it, per the spec's own
"AI Teacher is temporarily offline" requirement. To enable it, get an
API key and set it as an environment variable before starting the server:

```
export ANTHROPIC_API_KEY=sk-ant-...
python3 server.py
```

Or for an OpenAI-compatible provider:
```
export AI_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python3 server.py
```

No key is ever stored in the database or sent to the browser — it's
read from the environment on the server only.

## What's implemented

| Feature | How |
|---|---|
| Onboarding, subjects, exam countdown | SQLite, no AI needed |
| Study timer + Focus Mode | Tracks tab-switch interruptions automatically |
| Document Library (PDF/DOCX/TXT/notes) | Real text extraction (pypdf/python-docx), full-text search via SQLite FTS5 — this is what grounds the AI Teacher in your actual uploaded material instead of guessing |
| YouTube learning | Paste the transcript (via YouTube's own "Show transcript" button) — no network access here to fetch captions automatically, so this is the working alternative; it's then processed exactly like any other document |
| AI Teacher (chat) | Needs an API key (see above). Grounded in your Library when "Use my documents" is checked |
| Voice Tutor ("Talk to Teacher") | Your browser's built-in speech recognition + text-to-speech — no server/cloud speech API needed, works the moment the AI Teacher is on |
| AI Examiner (quiz generation) | Needs an API key. Falls back to manual question entry when offline |
| Spaced repetition quizzing | Simplified SM-2 algorithm, works with manual or AI-generated questions, no AI needed to run it |
| Estimated Mastery + Grade Forecast | Transparent, explainable formula (quiz accuracy + consistency + retention) — no AI needed, matches spec section 12/13 exactly |
| Weekly Report | Auto-generated stats every time you open it; narrative is AI-written if a key is configured, otherwise a clear template — both are real numbers, never fabricated |
| Weekly Learning Agenda | Goal tracking per subject/topic |
| Adaptive daily schedule | Rule-based priority engine (exam proximity + weakness + staleness) — the "today's mission" on your dashboard |

## What's genuinely not possible without extra setup

- **Native Android alarms/widgets** — this is a web app, not an Android
  app (see the Kotlin version elsewhere in this repo for those).
  Browser push notifications are the closest web equivalent and
  aren't wired up here.
- **Automatic YouTube transcript fetching** — needs either the
  `youtube-transcript-api` package or real internet access; paste
  the transcript instead (see above).
- **Cloud sync across devices** — this is a single local SQLite file.

## Structure

```
web/
  server.py       — HTTP routing
  db.py           — schema (SQLite + FTS5)
  ai_provider.py  — pluggable AI Teacher/Examiner (Anthropic/OpenAI-compatible)
  mastery.py      — mastery engine + grade forecast (no AI)
  scheduler.py    — adaptive daily schedule (no AI)
  documents.py    — PDF/DOCX/TXT extraction + full-text search
  html/           — index.html, style.css, app.js (vanilla JS SPA)
  data/           — zimstudy.db (gitignored)
```

