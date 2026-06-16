"""
Test: Team Inbox helpers + human-takeover webhook behavior.
Ensures: when a human has taken over a conversation, an inbound WhatsApp
message is stored for the inbox and the bot does NOT reply.
"""
import app.routers.whatsapp as wa
from app.routers.conversations import _channel, _wa_to, _last_message


class _Session:
    def __init__(self, human=False):
        self.human_handling = human
        self.messages = []
        self.unread_count = 0
        self.patient_phone = None
        self.session_token = "wa:923001234567"


class TestInboxHelpers:
    def test_channel_detection(self):
        assert _channel("wa:923001234567") == "whatsapp"
        assert _channel("a1b2-uuid") == "web"

    def test_wa_to_extracts_number(self):
        assert _wa_to("wa:923001234567") == "923001234567"
        assert _wa_to("web-uuid") == ""

    def test_last_message_preview(self):
        s = _Session()
        s.messages = [{"role": "user", "content": "hello there"}]
        assert _last_message(s)["preview"] == "hello there"

    def test_store_inbound_appends_and_bumps_unread(self):
        s = _Session()
        wa._store_inbound(s, "I need to reschedule")
        assert s.messages[-1] == {"role": "user", "content": "I need to reschedule"}
        assert s.unread_count == 1


class TestHumanTakeover:
    def test_human_mode_stores_message_and_skips_bot(self, monkeypatch):
        """The core guarantee: in human mode the bot must NOT reply."""
        session = _Session(human=True)

        monkeypatch.setattr(wa, "_load_context_for_phone",
                            lambda pnid: (object(), object(), []))
        monkeypatch.setattr(wa, "_get_or_create_session",
                            lambda wa_from, b, t, db: session)

        class _DB:
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
        monkeypatch.setattr(wa, "SessionLocal", lambda: _DB())

        sent = []
        monkeypatch.setattr(wa, "_send_whatsapp_reply",
                            lambda *a, **k: sent.append(a))
        # If the bot ran, this would be invoked — assert it never is.
        called = {"brain": False}
        def _brain(*a, **k):
            called["brain"] = True
            return ("reply", "intent", "en")
        monkeypatch.setattr(wa, "handle_turn", _brain)

        wa._handle_text("923001234567", "can a human help me?", "PNID_A")

        assert called["brain"] is False, "bot must stay silent during human takeover"
        assert not sent, "no automated reply should be sent in human mode"
        assert session.messages[-1]["content"] == "can a human help me?"
        assert session.unread_count == 1

    def test_bot_mode_still_replies(self, monkeypatch):
        session = _Session(human=False)
        monkeypatch.setattr(wa, "_load_context_for_phone",
                            lambda pnid: (object(), object(), []))
        monkeypatch.setattr(wa, "_get_or_create_session",
                            lambda wa_from, b, t, db: session)

        class _DB:
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
        monkeypatch.setattr(wa, "SessionLocal", lambda: _DB())

        class _Guard:
            allowed = True
            sanitized_message = "hi"
            blocked_reason = None
        monkeypatch.setattr(wa, "run_input_guard", lambda *a, **k: _Guard())
        monkeypatch.setattr(wa, "handle_turn", lambda *a, **k: ("Hello!", "general", "en"))

        sent = []
        monkeypatch.setattr(wa, "_send_whatsapp_reply", lambda *a, **k: sent.append(a))

        wa._handle_text("923001234567", "hi", "PNID_A")

        assert sent, "bot should reply when not in human mode"
        assert sent[0][1] == "Hello!"
