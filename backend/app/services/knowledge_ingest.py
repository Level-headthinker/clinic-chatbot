"""Ingest documents and web pages into the clinic knowledge base.

A clinic can upload a PDF/DOCX/TXT or paste a web link; we extract the text,
split it into reasonably sized chunks, and store each chunk as a KnowledgeEntry.
Because the existing retrieval (services/knowledge_retrieval.py) already does
full-text search over knowledge_base, ingested content becomes searchable by the
bot immediately — no new retrieval path needed.

Each ingest shares one ``source_ref`` (a UUID) so all chunks from the same file
or link can be listed and deleted together.
"""
from __future__ import annotations

import io
import ipaddress
import re
import socket
import uuid
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app.models.knowledge import KnowledgeEntry

# Safety caps.
MAX_CHARS = 120_000          # ignore anything past this much extracted text
CHUNK_CHARS = 1_500          # target size of each stored chunk
MAX_CHUNKS = 120             # never create more than this many entries per source


# ── Text extraction ─────────────────────────────────────────────────────────────

class IngestError(Exception):
    """Raised with a user-safe message when extraction/fetch fails."""


def extract_text_from_file(filename: str, raw: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(raw)
    if name.endswith(".docx"):
        return _extract_docx(raw)
    if name.endswith((".txt", ".md", ".csv")):
        return raw.decode("utf-8", errors="replace")
    raise IngestError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")


def _extract_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise IngestError("PDF support isn't installed on the server.")
    try:
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        raise IngestError("Could not read that PDF — it may be scanned or corrupted.")


def _extract_docx(raw: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        raise IngestError("DOCX support isn't installed on the server.")
    try:
        document = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:
        raise IngestError("Could not read that DOCX file.")


# ── Web page extraction ─────────────────────────────────────────────────────────

class _TextHTMLParser(HTMLParser):
    """Collect visible text; drop script/style/head and add breaks on block tags."""
    _SKIP = {"script", "style", "head", "noscript", "svg"}
    _BLOCK = {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}

    def __init__(self):
        super().__init__()
        self._skipping = 0
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skipping += 1
        if tag == "title":
            self._in_title = True
        if tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skipping:
            self._skipping -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:                # title lives inside <head> (skipped) — grab it first
            self.title += data
            return
        if self._skipping:
            return
        text = data.strip()
        if text:
            self.parts.append(text)


def _guard_url(url: str) -> str:
    """Allow only public http(s) URLs — blocks SSRF to internal/loopback hosts."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise IngestError("Enter a valid http(s) link.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise IngestError("Could not resolve that website address.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise IngestError("That address isn't allowed.")
    return url


def extract_text_from_url(url: str) -> tuple[str, str]:
    """Return (title, text) for a public web page."""
    _guard_url(url)
    try:
        with httpx.Client(timeout=15, follow_redirects=True, headers={
            "User-Agent": "ClinicBot-KnowledgeFetcher/1.0",
        }) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError:
        raise IngestError("Could not fetch that page. Check the link and try again.")

    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise IngestError("That link isn't a readable web page.")

    parser = _TextHTMLParser()
    parser.feed(resp.text)
    title = (parser.title or url).strip()[:200]
    text = re.sub(r"\n{3,}", "\n\n", " ".join(parser.parts))
    return title, text


# ── Chunking + storage ──────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    text = re.sub(r"[ \t]+", " ", (text or "")).strip()
    if not text:
        return []
    text = text[:MAX_CHARS]
    paragraphs = re.split(r"\n\s*\n|\n", text)
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # A single huge paragraph: hard-split it.
        while len(para) > size:
            chunks.append(para[:size])
            para = para[size:]
        if len(buf) + len(para) + 1 > size:
            if buf:
                chunks.append(buf.strip())
            buf = para
        else:
            buf = f"{buf} {para}".strip()
    if buf:
        chunks.append(buf.strip())
    return chunks[:MAX_CHUNKS]


def ingest_text(db, *, tenant_id, branch_id, source_type: str,
                source_name: str, text: str, category: str | None = None) -> dict:
    """Chunk text and store it as knowledge entries sharing one source_ref."""
    chunks = chunk_text(text)
    if not chunks:
        raise IngestError("No readable text was found.")

    source_ref = uuid.uuid4()
    label = source_name[:400]
    for i, chunk in enumerate(chunks, 1):
        title = f"{label} (part {i})" if len(chunks) > 1 else label
        db.add(KnowledgeEntry(
            tenant_id=tenant_id,
            branch_id=branch_id,
            question=title[:500],
            answer=chunk,
            category=(category or {"document": "Document", "web": "Web page"}.get(source_type)),
            is_active=True,
            source_type=source_type,
            source_name=label,
            source_ref=source_ref,
        ))
    db.commit()
    return {"source_ref": str(source_ref), "source_name": label,
            "source_type": source_type, "chunks": len(chunks)}
