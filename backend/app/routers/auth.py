# Two API endpoints — register a new clinic and login.
# Register creates the tenant and admin user together in one step.
# Login checks credentials and returns a JWT token.
import re
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.database import get_db
from app.config import settings
from app.models.branch import Branch
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import (
    create_access_token,
    create_password_reset_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from app.services.email import send_password_reset_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Auth"])


def _resolve_branch_slug(user, tenant, db) -> str:
    """Return the branch slug the user's chatbot embed should use.

    Branch-scoped users → their assigned branch slug.
    Tenant-level users  → the main branch slug (falls back to tenant slug).
    """
    if user.branch_id:
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
        if branch:
            return branch.slug
    main = db.query(Branch).filter(
        Branch.tenant_id == tenant.id,
        Branch.is_main_branch == True,
    ).first()
    return main.slug if main else tenant.slug


def _client_key(request: Request, suffix: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{suffix}"


def _enforce_rate_limit(key: str, max_attempts: int, window_seconds: int):
    # Shared limiter — Redis-backed across workers when REDIS_URL is set,
    # in-memory otherwise.
    from app.services.rate_limit import rate_limit_allow
    if not rate_limit_allow(key, max_attempts, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later."
        )


class RegisterRequest(BaseModel):
    clinic_name: str
    clinic_slug: str
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str
    whatsapp_number: Optional[str] = None   # clinic's own WA number (display/onboarding)

    @field_validator("whatsapp_number")
    @classmethod
    def whatsapp_format(cls, v):
        if not v:
            return v
        cleaned = re.sub(r"[\s\-()]", "", v)
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise ValueError("WhatsApp number must be 10–15 digits, optionally starting with +")
        return cleaned

    @field_validator("admin_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v

    @field_validator("clinic_slug")
    @classmethod
    def slug_format(cls, v):
        if not re.match(r"^[a-z0-9\-]+$", v):
            raise ValueError("Slug may only contain lowercase letters, numbers, and hyphens")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    tenant_id: str
    tenant_slug: str
    branch_slug: str
    user_name: str
    user_email: str
    is_superadmin: bool
    role: str
    doctor_id: Optional[str] = None
    plan: str = "starter"


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_slug: Optional[str]
    branch_slug: Optional[str]
    is_superadmin: bool
    doctor_id: Optional[str] = None
    plan: str = "starter"


@router.post("/register")
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    _enforce_rate_limit(
        _client_key(request, "register"),
        max_attempts=5,
        window_seconds=3600,
    )
    existing = db.query(Tenant).filter(
        Tenant.slug == data.clinic_slug
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Clinic slug already taken")

    from sqlalchemy import func as sa_func
    admin_email = data.admin_email.strip().lower()
    existing_user = db.query(User).filter(
        sa_func.lower(User.email) == admin_email
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    tenant = Tenant(
        name=data.clinic_name,
        slug=data.clinic_slug,
        bot_name=f"{data.clinic_name} Bot",
        whatsapp_number=data.whatsapp_number,
    )
    db.add(tenant)
    db.flush()

    main_branch = Branch(
        tenant_id=tenant.id,
        name=data.clinic_name,
        slug=data.clinic_slug,
        is_main_branch=True,
    )
    db.add(main_branch)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=admin_email,
        hashed_password=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        role="admin",
        # branch_id stays NULL — admin has tenant-level access to all branches
    )
    db.add(user)
    db.commit()
    db.refresh(tenant)

    # Start the 3-day free trial immediately.
    try:
        from app.services.subscription_service import get_or_create_subscription
        get_or_create_subscription(db, tenant)
    except Exception:
        db.rollback()  # never block registration on billing setup

    # Welcome email (best-effort — never block sign-up). Runs async in email.py.
    try:
        login_link = f"{settings.APP_BASE_URL.rstrip('/')}/login"
        send_welcome_email(admin_email, tenant.name, data.admin_full_name, login_link)
    except Exception:
        pass

    return {
        "message": "Clinic registered successfully",
        "tenant_id": str(tenant.id),
        "slug": tenant.slug
    }


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    _enforce_rate_limit(
        _client_key(request, f"login:{form_data.username.lower()}"),
        max_attempts=10,
        window_seconds=300,
    )
    from sqlalchemy import func as sa_func
    user = db.query(User).filter(
        sa_func.lower(User.email) == form_data.username.strip().lower()
    ).first()

    # Always run one bcrypt verification so a missing account takes the same
    # time as a wrong password (no user-enumeration timing oracle).
    _DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO7ZBlS3nq3yU0EHCS7iLTC0bWQH3pW7e"
    hashed = user.hashed_password if user else _DUMMY_HASH
    if not verify_password(form_data.password, hashed) or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic is disabled"
        )

    token = create_access_token(data={"sub": str(user.id), "ver": user.token_version or 0})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="none" if request.url.scheme == "https" else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": str(user.tenant_id),
        "tenant_slug": tenant.slug,
        "branch_slug": _resolve_branch_slug(user, tenant, db),
        "user_name": user.full_name,
        "user_email": user.email,
        "is_superadmin": user.is_superadmin,
        "role": user.role,
        "doctor_id": str(user.doctor_id) if user.doctor_id else None,
        "plan": tenant.plan or "starter",
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(
        "access_token",
        secure=request.url.scheme == "https",
        samesite="none" if request.url.scheme == "https" else "lax",
    )
    return {"message": "Logged out"}


# ── Self-service password reset ─────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Email a reset link. Always returns the same message — never reveals
    whether an email is registered (no account enumeration)."""
    _enforce_rate_limit(_client_key(request, "forgot"), max_attempts=5, window_seconds=900)

    from sqlalchemy import func as sa_func
    email = data.email.strip().lower()
    user = db.query(User).filter(
        sa_func.lower(User.email) == email, User.is_active == True
    ).first()
    if user:
        # Fingerprint the current hash into the token → the link dies the moment
        # the password changes (single-use).
        token = create_password_reset_token(str(user.id), pw_hash=user.hashed_password)
        link = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={token}"
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        send_password_reset_email(user.email, link, tenant.name if tenant else "ClinicBot")

    return {"message": "If that email is registered, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(_client_key(request, "reset"), max_attempts=10, window_seconds=900)

    user_id = verify_password_reset_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    # Single-use check: token must match the CURRENT password hash — a link that
    # was already used (or issued before an earlier reset) is spent.
    if verify_password_reset_token(data.token, current_pw_hash=user.hashed_password) is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user.hashed_password = hash_password(data.new_password)
    # Kill every existing session/JWT for this account (stolen tokens included).
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    return {"message": "Password updated. You can now log in with your new password."}


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=str(current_user.tenant_id),
        tenant_slug=tenant.slug if tenant else None,
        branch_slug=_resolve_branch_slug(current_user, tenant, db) if tenant else None,
        is_superadmin=current_user.is_superadmin,
        doctor_id=str(current_user.doctor_id) if current_user.doctor_id else None,
        plan=tenant.plan if tenant else "starter",
    )
