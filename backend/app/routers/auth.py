# Two API endpoints — register a new clinic and login.
# Register creates the tenant and admin user together in one step.
# Login checks credentials and returns a JWT token.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    clinic_name: str
    clinic_slug: str
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    tenant_id: str
    tenant_slug: str
    user_name: str
    user_email: str
    is_superadmin: bool


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Tenant).filter(
        Tenant.slug == data.clinic_slug
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Clinic slug already taken"
        )

    existing_user = db.query(User).filter(
        User.email == data.admin_email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    tenant = Tenant(
        name=data.clinic_name,
        slug=data.clinic_slug,
        bot_name=f"{data.clinic_name} Bot"
    )
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=data.admin_email,
        hashed_password=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(tenant)

    return {
        "message": "Clinic registered successfully",
        "tenant_id": str(tenant.id),
        "slug": tenant.slug
    }


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Account is disabled"
        )

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic is disabled"
        )

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": str(user.tenant_id),
        "tenant_slug": tenant.slug,
        "user_name": user.full_name,
        "user_email": user.email,
        "is_superadmin": user.is_superadmin
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tenant_id": str(current_user.tenant_id),
        "tenant_slug": tenant.slug if tenant else None,
        "is_superadmin": current_user.is_superadmin
    }
