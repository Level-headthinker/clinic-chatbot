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