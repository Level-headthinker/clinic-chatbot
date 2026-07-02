# Handles login security: password hashing, JWT creation, and current-user lookup.

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8")[:72],
            hashed.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


# ── Password reset tokens ────────────────────────────────────
# A short-lived, purpose-scoped JWT. No DB column needed; the token carries the
# user id + a "reset" purpose (so it can't be used as a login token) + a
# fingerprint of the CURRENT password hash — so the link becomes single-use:
# the moment the password changes, the fingerprint no longer matches and the
# same link (or a stolen copy) is dead.

def _pw_fingerprint(hashed_password: str) -> str:
    import hashlib
    return hashlib.sha256((hashed_password or "").encode()).hexdigest()[:16]


def create_password_reset_token(user_id: str, pw_hash: str = "",
                                expires_minutes: int = 30) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(
        {"sub": str(user_id), "purpose": "reset", "exp": expire,
         "pwf": _pw_fingerprint(pw_hash)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_password_reset_token(token: str, current_pw_hash: Optional[str] = None) -> Optional[str]:
    """Return the user id if the token is a valid, unexpired reset token — and,
    when ``current_pw_hash`` is given, only if the password hasn't changed since
    the token was issued (single-use)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != "reset":
        return None
    if current_pw_hash is not None:
        if payload.get("pwf") != _pw_fingerprint(current_pw_hash):
            return None  # password already changed → link is spent
    return payload.get("sub")


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = token or request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if user is None:
        raise credentials_exception
    # Session invalidation: the token carries the token_version it was minted
    # with; a password reset bumps the user's version, killing every older
    # token (a stolen JWT dies the moment the password is changed).
    if payload.get("ver", 0) != (user.token_version or 0):
        raise credentials_exception
    return user


def require_admin_user(current_user: User = Depends(get_current_user)):
    """Any authenticated user with admin or higher role. Includes branch admins."""
    if current_user.is_superadmin or current_user.role in ("admin", "branch_admin", "superadmin"):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def require_doctor_user(current_user: User = Depends(get_current_user)):
    """Doctor portal — only users with role='doctor' and a linked doctor_id."""
    if current_user.role == "doctor" and current_user.doctor_id:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Doctor access only",
    )


def require_tenant_admin(current_user: User = Depends(get_current_user)):
    """Tenant-level admin only — NOT branch admins. Used for branch creation/deletion."""
    if current_user.is_superadmin or current_user.role in ("admin", "superadmin"):
        if current_user.branch_id is None:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only clinic-level admins can perform this action",
    )
