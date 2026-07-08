"""
Test: report_error makes swallowed failures visible without ever raising.
Every best-effort code path routes through it, so it must be bullet-proof.
"""
import logging

from app.observability import report_error


class TestReportError:
    def test_logs_at_error_level(self, caplog):
        with caplog.at_level(logging.ERROR, logger="clinicbot"):
            report_error("something failed", ValueError("boom"), tenant="t1")
        assert any(r.levelno == logging.ERROR for r in caplog.records)
        assert "something failed" in caplog.text
        assert "tenant=t1" in caplog.text          # context included
        assert "boom" in caplog.text               # exception surfaced

    def test_works_without_exception(self, caplog):
        with caplog.at_level(logging.ERROR, logger="clinicbot"):
            report_error("plain alert")
        assert "plain alert" in caplog.text

    def test_never_raises_on_bad_input(self):
        # Non-serialisable context / weird exc must not blow up the caller.
        class Weird:
            def __str__(self):
                raise RuntimeError("cannot stringify")
        report_error("msg", Exception("x"), obj=Weird())   # must not raise
        report_error("msg", None)                            # must not raise
