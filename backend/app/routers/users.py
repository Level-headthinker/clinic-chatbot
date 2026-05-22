import re
from typing import Literal, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Branch
from app.models.user import User
from app.services.auth import hash_password, require_admin_user

router = APIRouter(prefix="/users", tags=["Users"])

UserRole = Literal["admin", "staff"]


# ── Schemas ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = "staff"
    branch_id: Optional[str] = None  # null = tenant-level access

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    branch_id: Optional[str] = None   # pass "" or null to remove branch restriction


class PasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    branch_id: Optional[str]
    branch_name: Optional[str]
    is_active: bool
    is_superadmin: bool

    model_config = {"from_attributes": True}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format(user: User, branch: Optional[Branch] = None) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        branch_id=str(user.branch_id) if user.branch_id else None,
        branch_name=branch.name if branch else None,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
    )


def _resolve_branch(branch_id: Optional[str], tenant_id, db: Session) -> Optional[Branch]:
    """Validate branch_id belongs to the tenant and return the Branch, or None."""
    if not branch_id:
        return None
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.tenant_id == tenant_id,
        Branch.is_active == True,
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


def _get_user_or_404(user_id: str, tenant_id, db: Session) -> User:
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id,
        User.is_superadmin == False,  # never expose superadmin accounts via this router
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _branch_map(users: list[User], db: Session) -> dict:
    """Fetch branch names for a list of users in one query."""
    branch_ids = {u.branch_id for u in users if u.branch_id}
    if not branch_ids:
        return {}
    branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
    return {b.id: b for b in branches}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=List[UserResponse])
def list_users(
    branch_id: Optional[str] = None,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """List all staff for the current tenant. Optionally filter by branch."""
    query = db.query(User).filter(
        User.tenant_id == current_user.tenant_id,
        User.is_superadmin == False,
    )
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    elif current_user.branch_id is not None:
        # Branch-scoped admins only see their own branch's staff
        query = query.filter(User.branch_id == current_user.branch_id)

    users = query.order_by(User.created_at.asc()).all()
    branches = _branch_map(users, db)
    return [_format(u, branches.get(u.branch_id)) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Create a new staff account within the current tenant."""
    branch = _resolve_branch(data.branch_id, current_user.tenant_id, db)

    # Branch-scoped admins can only create users for their own branch
    if current_user.branch_id is not None:
        if data.branch_id and str(current_user.branch_id) != data.branch_id:
            raise HTTPException(status_code=403, detail="Cannot create users for another branch")
        branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()

    user = User(
        tenant_id=current_user.tenant_id,
        branch_id=branch.id if branch else None,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email is already registered")
    db.refresh(user)
    return _format(user, branch)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, current_user.tenant_id, db)
    branch = db.query(Branch).filter(Branch.id == user.branch_id).first() if user.branch_id else None
    return _format(user, branch)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Update name, role, or branch assignment. Pass branch_id=null to grant tenant-level access."""
    user = _get_user_or_404(user_id, current_user.tenant_id, db)

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot modify your own account via this endpoint")

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.role is not None:
        user.role = data.role

    branch = None
    if "branch_id" in data.model_fields_set:
        branch = _resolve_branch(data.branch_id, current_user.tenant_id, db)
        user.branch_id = branch.id if branch else None
    elif user.branch_id:
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()

    db.commit()
    db.refresh(user)
    return _format(user, branch)


@router.patch("/{user_id}/toggle", response_model=UserResponse)
def toggle_user(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Activate or deactivate a staff account."""
    user = _get_user_or_404(user_id, current_user.tenant_id, db)

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    branch = db.query(Branch).filter(Branch.id == user.branch_id).first() if user.branch_id else None
    return _format(user, branch)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: str,
    data: PasswordReset,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Admin resets another user's password."""
    user = _get_user_or_404(user_id, current_user.tenant_id, db)

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Use a dedicated profile endpoint to change your own password")

    user.hashed_password = hash_password(data.new_password)
    db.commit()
