import pytest
import sys
import os

# Make sure backend/ is on the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fake doctor for tests ────────────────────────────────────
class FakeDoctor:
    def __init__(self):
        self.id = "doctor-uuid-001"
        self.name = "Dr. Ahmed Khan"
        self.specialty = "General Physician"
        self.treatments = ["fever", "flu", "diabetes", "blood pressure"]
        self.timings = [
            {"day": "monday", "from": "9:00 AM", "to": "5:00 PM"},
            {"day": "wednesday", "from": "9:00 AM", "to": "5:00 PM"},
            {"day": "friday", "from": "9:00 AM", "to": "1:00 PM"},
        ]
        self.fee = "1000"
        self.is_active = True
        self.tenant_id = "tenant-uuid-001"


@pytest.fixture
def fake_doctor():
    return FakeDoctor()


@pytest.fixture
def sample_clinic_info():
    return (
        "Clinic Name: Test Clinic\n"
        "Bot Name: TestBot\n"
        "Welcome Message: Welcome!\n"
        "Clinic Timings: Monday to Saturday, 9am to 9pm\n"
        "Emergency: Call 1122"
    )


@pytest.fixture
def sample_doctors_info():
    return "- Dr. Ahmed Khan | General Physician | Fee: 1000 | Monday 9AM-5PM"


@pytest.fixture
def sample_session_token():
    return "test-session-abc-123"


@pytest.fixture(autouse=True)
def reset_rate_store():
    """
    Reset rate limit store before each test so tests don't interfere.
    autouse=True means this runs automatically for every test.
    """
    from app.services.input_guard import _rate_store, _last_message_store
    _rate_store.clear()
    _last_message_store.clear()
    yield
    _rate_store.clear()
    _last_message_store.clear()


# ── Integration-test scaffolding (opt-in: needs a disposable Postgres) ──────────
# The two things worth an *integration* test — the double-booking guard and the
# webhook idempotency check — only behave correctly against real Postgres:
#   • the anti-double-book guard is a PARTIAL UNIQUE INDEX (postgresql_where),
#     which SQLite silently ignores, so it must run on Postgres to mean anything.
# These fixtures are shared by the integration test modules.
import os
import uuid as _uuid

import pytest

needs_db = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="set TEST_DATABASE_URL to a DISPOSABLE postgres database to run",
)


@pytest.fixture()
def db_session():
    """A real Postgres session with the full schema created. Rolls back and
    disposes after each test. Requires TEST_DATABASE_URL (see `needs_db`)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.fixture()
def make_clinic(db_session):
    """Factory: create an isolated clinic (tenant + main branch + doctor) with
    unique slugs so repeated runs never collide. Returns (tenant, branch, doctor)."""
    from app.models.branch import Branch
    from app.models.doctor import Doctor
    from app.models.tenant import Tenant

    def _make(label="clinic"):
        suffix = _uuid.uuid4().hex[:8]
        t = Tenant(name=f"{label} {suffix}", slug=f"{label}-{suffix}")
        db_session.add(t); db_session.flush()
        b = Branch(tenant_id=t.id, name=label, slug=t.slug, is_main_branch=True)
        db_session.add(b); db_session.flush()
        d = Doctor(tenant_id=t.id, branch_id=b.id, name=f"Dr {label}", specialty="GP")
        db_session.add(d); db_session.flush()
        return t, b, d

    return _make