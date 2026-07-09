"""
Test: public self-booking slot validation
Ensures: a booking may only claim a slot the doctor actually offers — future,
on a working day, inside hours, on the 30-minute grid, not already taken.
Previously ANY datetime (3 AM, past dates) was written straight to the diary.
"""
from datetime import datetime, timedelta

from app.routers.booking import _slot_is_offered, _PHONE_OK


class _NoBookedQuery:
    def filter(self, *a, **k):
        return self

    def first(self):
        return None

    def count(self):
        return 0   # capacity check: no seats taken in this slot


class _FakeDB:
    def query(self, model):
        return _NoBookedQuery()


class _FakeDoctor:
    id = "doc-1"
    timings = [{"day": "monday", "from": "9:00 AM", "to": "5:00 PM"}]


def _next_monday_at(hour, minute=0):
    now = datetime.now()
    days = (0 - now.weekday()) % 7 or 7  # always a FUTURE Monday
    return (now + timedelta(days=days)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


class TestSlotValidation:
    def test_valid_on_grid_slot_accepted(self):
        slot = _next_monday_at(10, 0)
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is True

    def test_past_slot_rejected(self):
        slot = datetime.now() - timedelta(days=1)
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is False

    def test_off_grid_time_rejected(self):
        slot = _next_monday_at(10, 17)  # not a 30-min boundary
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is False

    def test_outside_working_hours_rejected(self):
        slot = _next_monday_at(3, 0)  # 3 AM
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is False

    def test_wrong_weekday_rejected(self):
        slot = _next_monday_at(10, 0) + timedelta(days=1)  # Tuesday
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is False

    def test_far_future_rejected(self):
        slot = _next_monday_at(10, 0) + timedelta(days=120)
        assert _slot_is_offered(_FakeDoctor(), slot, _FakeDB(), "t1") is False


class TestPhoneValidation:
    def test_pakistani_mobile_ok(self):
        assert _PHONE_OK.match("03001234567")
        assert _PHONE_OK.match("+923001234567")

    def test_garbage_rejected(self):
        assert not _PHONE_OK.match("not-a-phone")
        assert not _PHONE_OK.match("12")
