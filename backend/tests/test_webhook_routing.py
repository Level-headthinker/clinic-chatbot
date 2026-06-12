"""
Test: WhatsApp webhook clinic routing (phone_number_id → clinic)
Ensures: an unregistered phone_number_id resolves to NOTHING (fail closed) —
the old behavior fell back to "first active branch in the database", which
answered with another clinic's doctors and booked into the wrong tenant.
"""
import app.routers.whatsapp as whatsapp


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self._result if not isinstance(self._result, list) else (
            self._result[0] if self._result else None
        )

    def all(self):
        return self._result if isinstance(self._result, list) else (
            [self._result] if self._result else []
        )


class _FakeDB:
    """Returns canned results per model class; records which models were queried."""
    def __init__(self, results_by_model):
        self.results = results_by_model
        self.queried = []

    def query(self, model):
        self.queried.append(model.__name__)
        return _FakeQuery(self.results.get(model.__name__))

    def close(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class TestWebhookRouting:
    def test_unregistered_number_fails_closed(self, monkeypatch):
        """No mapping + no legacy branch match → (None, None, []) — never
        another clinic's branch."""
        db = _FakeDB({"WhatsAppNumberMapping": None, "Branch": None})
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)

        branch, tenant, doctors = whatsapp._load_context_for_phone("999999999999999")

        assert branch is None and tenant is None and doctors == []
        # The old vulnerable code issued a second, unfiltered Branch query as a
        # fallback. Fail-closed must stop at the legacy exact-match lookup.
        assert db.queried.count("Branch") <= 1, \
            "SECURITY FAILURE: fallback branch lookup still present"

    def test_mapped_number_resolves_its_clinic(self, monkeypatch):
        branch = _Obj(id="b1", tenant_id="t1", is_active=True)
        tenant = _Obj(id="t1", is_active=True)
        mapping = _Obj(tenant_id="t1", branch_id="b1", is_active=True)
        db = _FakeDB({
            "WhatsAppNumberMapping": mapping,
            "Branch": branch,
            "Tenant": tenant,
            "Doctor": [_Obj(id="d1", name="Ahmed")],
        })
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)

        got_branch, got_tenant, doctors = whatsapp._load_context_for_phone("111222333444555")

        assert got_branch is branch
        assert got_tenant is tenant
        assert len(doctors) == 1


class TestMessageQuota:
    def _mapping(self, used, limit, reset=None, active=True):
        return _Obj(
            is_active=active,
            messages_used_this_month=used,
            message_limit_monthly=limit,
            limit_reset_date=reset,
        )

    def test_under_limit_allowed_and_counted(self, monkeypatch):
        from datetime import datetime, timedelta, timezone
        mapping = self._mapping(5, 1000, datetime.now(timezone.utc) + timedelta(days=10))
        db = _FakeDB({"WhatsAppNumberMapping": mapping})
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)

        allowed, just_hit = whatsapp._check_message_quota("pn1")
        assert allowed is True and just_hit is False
        assert mapping.messages_used_this_month == 6

    def test_at_limit_blocked(self, monkeypatch):
        from datetime import datetime, timedelta, timezone
        mapping = self._mapping(1000, 1000, datetime.now(timezone.utc) + timedelta(days=10))
        db = _FakeDB({"WhatsAppNumberMapping": mapping})
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)

        allowed, _ = whatsapp._check_message_quota("pn1")
        assert allowed is False
        assert mapping.messages_used_this_month == 1000  # not incremented past limit

    def test_new_month_resets_counter(self, monkeypatch):
        from datetime import datetime, timedelta, timezone
        mapping = self._mapping(1000, 1000, datetime.now(timezone.utc) - timedelta(days=1))
        db = _FakeDB({"WhatsAppNumberMapping": mapping})
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)

        allowed, _ = whatsapp._check_message_quota("pn1")
        assert allowed is True
        assert mapping.messages_used_this_month == 1
        assert mapping.limit_reset_date > datetime.now(timezone.utc)

    def test_unmapped_number_not_limited(self, monkeypatch):
        db = _FakeDB({"WhatsAppNumberMapping": None})
        monkeypatch.setattr(whatsapp, "SessionLocal", lambda: db)
        allowed, _ = whatsapp._check_message_quota("legacy-number")
        assert allowed is True
