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
from app.services.auth import hash_password, verify_password, create_access_token

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
    user_name: str


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

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": str(user.tenant_id),
        "user_name": user.full_name
    }


@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    return {"message": "Auth working"}