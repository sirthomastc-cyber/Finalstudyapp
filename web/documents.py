"""
documents.py — text extraction for uploaded books/notes/past papers, and
the FTS5-backed search that stands in for RAG retrieval (spec section 25)
without needing an embeddings/vector-database service.

PDF and DOCX extraction are optional extras (pypdf / python-docx). If
they aren't installed, .txt/.md still work with zero setup, and PDF/DOCX
uploads get a clear error telling the user what to install — nothing
fails silently (spec section 30).
"""

import base64
import io


class ExtractionError(Exception):
    pass


def extract_text(filename, content_b64, doc_type_hint=None):
    """content_b64 is the file's raw bytes, base64-encoded (as sent by the browser)."""
    raw = base64.b64decode(content_b64)
    lower = filename.lower()

    if lower.endswith(".txt") or lower.endswith(".md"):
        return raw.decode("utf-8", errors="replace"), 1

    if lower.endswith(".pdf"):
        try:
            import pypdf
        except ImportError:
            raise ExtractionError(
                "PDF upload needs the 'pypdf' package. Install it with: pip install pypdf"
            )
        reader = pypdf.PdfReader(io.BytesIO(raw))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages), len(reader.pages)

    if lower.endswith(".docx"):
        try:
            import docx
        except ImportError:
            raise ExtractionError(
                "DOCX upload needs the 'python-docx' package. Install it with: pip install python-docx"
            )
        document = docx.Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in document.paragraphs)
        return text, 1

    raise ExtractionError(
        f"Unsupported file type for '{filename}'. Upload .txt, .md, .pdf, or .docx."
    )


def search(conn, query, subject=None, limit=8):
    """FTS5 search across uploaded documents. Returns short, cited excerpts —
    this is what lets the AI Teacher say 'your textbook, page X' truthfully
    instead of fabricating it, since it only ever sees text that was
    actually retrieved from the upload."""
    if not query.strip():
        return []

    safe_query = query.replace('"', '""')
    sql = """
        SELECT documents.id, documents.title, documents.doc_type, documents.subject,
               snippet(documents_fts, 1, '[', ']', '...', 24) AS excerpt
        FROM documents_fts
        JOIN documents ON documents.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
    """
    params = [f'"{safe_query}"']
    if subject:
        sql += " AND documents.subject = ?"
        params.append(subject)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        return []  # malformed FTS query — degrade gracefully rather than 500
    return [dict(r) for r in rows]
