"""
Test: WhatsApp replies are sent FROM the number that received the message.
Ensures multi-number works — a message to clinic A's number replies via A's
phone_number_id, not the single global META_PHONE_NUMBER_ID.
"""
import app.routers.whatsapp as wa


class _Resp:
    status_code = 200
    text = "ok"


def test_reply_uses_receiving_number(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr(wa.httpx, "post", fake_post)
    monkeypatch.setattr(wa.settings, "META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(wa.settings, "META_PHONE_NUMBER_ID", "GLOBAL_PNID")

    wa._send_whatsapp_reply("923001112223", "hello", from_pnid="CLINIC_A_PNID")

    assert "CLINIC_A_PNID/messages" in captured["url"]
    assert "GLOBAL_PNID" not in captured["url"], \
        "reply must go out from the receiving number, not the global one"


def test_reply_falls_back_to_global_when_no_pnid(monkeypatch):
    captured = {}
    monkeypatch.setattr(wa.httpx, "post", lambda url, **k: captured.update(url=url) or _Resp())
    monkeypatch.setattr(wa.settings, "META_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(wa.settings, "META_PHONE_NUMBER_ID", "GLOBAL_PNID")

    wa._send_whatsapp_reply("923001112223", "hello")  # legacy single-number path

    assert "GLOBAL_PNID/messages" in captured["url"]
