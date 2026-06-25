"""
Test: audit-trail helpers.
Snapshots must never leak secrets and must be JSON-serialisable, and field
snapshots must pull exactly the requested attributes.
"""
from types import SimpleNamespace
from app.services.audit import _clean, snapshot


class TestClean:
    def test_redacts_secrets(self):
        out = _clean({"name": "Ali", "hashed_password": "x", "token": "y", "secret": "z"})
        assert out == {"name": "Ali"}

    def test_none_passthrough(self):
        assert _clean(None) is None
        assert _clean({}) == {}

    def test_stringifies_non_primitives(self):
        import uuid
        uid = uuid.uuid4()
        out = _clean({"id": uid, "n": 5, "ok": True, "blank": None})
        assert out["id"] == str(uid)
        assert out["n"] == 5 and out["ok"] is True and out["blank"] is None


class TestSnapshot:
    def test_pulls_named_fields_only(self):
        obj = SimpleNamespace(name="Ali", phone="123", age=40, secret="hide")
        assert snapshot(obj, ["name", "phone"]) == {"name": "Ali", "phone": "123"}

    def test_missing_field_is_none(self):
        obj = SimpleNamespace(name="Ali")
        assert snapshot(obj, ["name", "phone"]) == {"name": "Ali", "phone": None}
