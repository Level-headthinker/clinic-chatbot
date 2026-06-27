"""
Test: knowledge-base document/web ingestion helpers.
Chunking must stay within size, file extraction must reject unknown types,
the SSRF guard must block internal hosts, and HTML must reduce to clean text.
"""
import pytest

from app.services import knowledge_ingest as ki


class TestChunking:
    def test_splits_long_text_within_size(self):
        chunks = ki.chunk_text("word " * 2000)
        assert len(chunks) > 1
        assert all(len(c) <= ki.CHUNK_CHARS for c in chunks)

    def test_empty_text_yields_nothing(self):
        assert ki.chunk_text("") == []
        assert ki.chunk_text("   \n\n  ") == []

    def test_caps_chunk_count(self):
        huge = ("para. " * 50 + "\n\n") * 500
        assert len(ki.chunk_text(huge)) <= ki.MAX_CHUNKS


class TestFileExtraction:
    def test_txt(self):
        assert "clinic" in ki.extract_text_from_file("a.txt", b"clinic hours 9-5")

    def test_unknown_type_rejected(self):
        with pytest.raises(ki.IngestError):
            ki.extract_text_from_file("a.exe", b"\x00\x01")


class TestSSRFGuard:
    @pytest.mark.parametrize("url", [
        "http://localhost/x",
        "http://127.0.0.1/x",
        "file:///etc/passwd",
        "ftp://example.com/x",
        "http://169.254.169.254/latest/meta-data/",
    ])
    def test_blocks_unsafe_urls(self, url):
        with pytest.raises(ki.IngestError):
            ki._guard_url(url)


class TestHtmlExtraction:
    def test_strips_script_style_and_keeps_text(self):
        p = ki._TextHTMLParser()
        p.feed("<html><head><title>Clinic</title><style>x{}</style></head>"
               "<body><h1>Pricing</h1><p>Consult is 2000.</p>"
               "<script>evil()</script></body></html>")
        text = " ".join(p.parts)
        assert "Pricing" in text and "Consult is 2000." in text
        assert "evil" not in text
        assert p.title == "Clinic"
