"""
Test: shared rate-limit + de-dup (in-memory fallback path).
These are the building blocks for cross-worker WhatsApp de-dup and brute-force
protection; verify the limit and the seen-once semantics.
"""
import time

from app.services import rate_limit as rl


def _reset():
    rl._hits.clear()
    rl._seen.clear()


class TestRateLimit:
    def test_allows_up_to_max_then_blocks(self):
        _reset()
        key = "u1"
        assert [rl.rate_limit_allow(key, 3, 60) for _ in range(5)] == [True, True, True, False, False]

    def test_separate_keys_independent(self):
        _reset()
        assert rl.rate_limit_allow("a", 1, 60) is True
        assert rl.rate_limit_allow("a", 1, 60) is False
        assert rl.rate_limit_allow("b", 1, 60) is True  # different key unaffected

    def test_window_resets(self):
        _reset()
        assert rl.rate_limit_allow("w", 1, 1) is True
        assert rl.rate_limit_allow("w", 1, 1) is False
        time.sleep(1.1)
        assert rl.rate_limit_allow("w", 1, 1) is True


class TestDedup:
    def test_seen_once(self):
        _reset()
        assert rl.dedup_seen("msg-1", 60) is False   # first time
        assert rl.dedup_seen("msg-1", 60) is True    # already seen
        assert rl.dedup_seen("msg-2", 60) is False   # different id

    def test_expires(self):
        _reset()
        assert rl.dedup_seen("x", 1) is False
        assert rl.dedup_seen("x", 1) is True
        time.sleep(1.1)
        assert rl.dedup_seen("x", 1) is False
