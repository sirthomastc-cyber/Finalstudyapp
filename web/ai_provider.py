"""
ai_provider.py — Pluggable AI provider layer for the AI Teacher / Examiner.

This follows the spec's own architecture requirement (section 24): never
hard-code around one provider, never put secret keys in client-facing
code, and configure the provider through the backend only.

No API key is stored anywhere in this repo or in the database. The key
is read from an environment variable at request time. If it's not set,
every function here returns None / raises AIUnavailable, and the server
responds with the spec's own required message: "AI Teacher is
temporarily offline" plus offline alternatives (see section 30).

Supported providers (set AI_PROVIDER to one of these):
  - "anthropic"  (needs ANTHROPIC_API_KEY)   — default
  - "openai"     (needs OPENAI_API_KEY)      — or any OpenAI-compatible
                                                endpoint via OPENAI_BASE_URL

Uses only the standard library (urllib) so no pip install is required
just to wire this up — only an API key.
"""

import json
import os
import urllib.request
import urllib.error


class AIUnavailable(Exception):
    """Raised when no AI provider is configured, or the call fails."""


def current_provider():
    provider = os.environ.get("AI_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return "anthropic", bool(os.environ.get("ANTHROPIC_API_KEY"))
    if provider == "openai":
        return "openai", bool(os.environ.get("OPENAI_API_KEY"))
    return provider, False


def is_configured():
    _, has_key = current_provider()
    return has_key


def _call_anthropic(system_prompt, messages, max_tokens=800):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIUnavailable("ANTHROPIC_API_KEY not set")

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise AIUnavailable(f"Anthropic API request failed: {e}")

    parts = [b["text"] for b in body.get("content", []) if b.get("type") == "text"]
    return "\n".join(parts).strip()


def _call_openai(system_prompt, messages, max_tokens=800):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AIUnavailable("OPENAI_API_KEY not set")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    payload = {"model": model, "messages": full_messages, "max_tokens": max_tokens}

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise AIUnavailable(f"OpenAI-compatible API request failed: {e}")

    return body["choices"][0]["message"]["content"].strip()


def chat(system_prompt, messages):
    """
    messages: list of {"role": "user"|"assistant", "content": "..."}
    Returns assistant text, or raises AIUnavailable.
    """
    provider, has_key = current_provider()
    if not has_key:
        raise AIUnavailable(f"No API key configured for provider '{provider}'")

    if provider == "anthropic":
        return _call_anthropic(system_prompt, messages)
    if provider == "openai":
        return _call_openai(system_prompt, messages)
    raise AIUnavailable(f"Unknown AI_PROVIDER '{provider}'")


# ---- Higher-level helpers used by server.py -----------------------------

TEACHER_SYSTEM_PROMPT = """You are the AI Teacher inside ZIMStudy AI, an app for \
ZIMSEC students. Teach clearly and patiently for the given subject and topic. \
When source material from the student's uploaded documents is provided, teach \
primarily from it and reference it (e.g. "your textbook, page 74"). Never invent \
page numbers or quotations — if the source doesn't cover something, say so \
plainly. Keep responses focused and exam-relevant. If the student says things \
like "explain it another way", "give me an example", or "test me", respond to \
that directly using the ongoing context."""

EXAMINER_SYSTEM_PROMPT = """You are the AI Examiner inside ZIMStudy AI. Generate \
ZIMSEC-style exam questions for the given subject, topic, and difficulty. Mix \
question types (multiple choice, short answer, application, calculation) where \
appropriate. Return ONLY valid JSON: a list of objects with keys "question", \
"answer", "question_type", "difficulty" (1-5). No prose outside the JSON."""


def teach(subject, topic, user_message, history, source_excerpts=None):
    context = ""
    if source_excerpts:
        context = "\n\nRelevant material from the student's uploaded documents:\n" + "\n---\n".join(source_excerpts)

    system = f"{TEACHER_SYSTEM_PROMPT}\n\nCurrent subject: {subject}\nCurrent topic: {topic}{context}"
    messages = history + [{"role": "user", "content": user_message}]
    return chat(system, messages)


def generate_quiz(subject, topic, difficulty, count=5, source_excerpts=None):
    context = ""
    if source_excerpts:
        context = "\n\nBase questions on this source material where relevant:\n" + "\n---\n".join(source_excerpts)

    system = EXAMINER_SYSTEM_PROMPT + context
    user = f"Generate {count} questions for subject '{subject}', topic '{topic}', difficulty {difficulty}/5."
    raw = chat(system, [{"role": "user", "content": user}])

    # Be forgiving about accidental markdown code fences around the JSON.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("expected a list")
        return parsed
    except json.JSONDecodeError:
        raise AIUnavailable("AI response wasn't valid JSON — try again")


def generate_exam(subject, topic, difficulty, count=10, source_excerpts=None):
    """Generate a formal assessment using the same provider and JSON contract."""
    context = ""
    if source_excerpts:
        context = "\n\nUse this source material where relevant:\n" + "\n---\n".join(source_excerpts)
    system = EXAMINER_SYSTEM_PROMPT + context + """
For this formal exam, every item MUST be objectively markable. Prefer multiple
choice questions with an "options" array and an "answer" containing the exact
correct option text. Also include a concise "explanation". Return only JSON.
"""
    user = f"Generate a formal ZIMSEC-style exam of {count} questions for '{subject}', topic '{topic}', difficulty {difficulty}/5."
    raw = chat(system, [{"role": "user", "content": user}])
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("expected a list")
        return parsed
    except (json.JSONDecodeError, ValueError):
        raise AIUnavailable("AI response wasn't valid exam JSON — try again")
