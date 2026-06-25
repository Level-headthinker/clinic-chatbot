"""
Test: password-reset token security.
A reset token must round-trip, but a normal login token must NOT be usable as
a reset token, and tampered/garbage tokens must be rejected.
"""
from app.services.auth import (
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token,
)


class TestResetToken:
    def test_valid_token_roundtrips(self):
        t = create_password_reset_token("user-abc")
        assert verify_password_reset_token(t) == "user-abc"

    def test_access_token_not_accepted_as_reset(self):
        # Critical: a login token (no 'reset' purpose) must not reset a password.
        at = create_access_token({"sub": "user-abc"})
        assert verify_password_reset_token(at) is None

    def test_garbage_rejected(self):
        assert verify_password_reset_token("not-a-token") is None
        assert verify_password_reset_token("") is None

    def test_tampered_token_rejected(self):
        t = create_password_reset_token("user-abc")
        assert verify_password_reset_token(t + "x") is None
