import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Branch
from app.models.user import User
from app.services.auth import get_current_user, require_admin_user, require_tenant_admin

router = APIRouter(prefix="/branches", tags=["Branches"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class BranchCreate(BaseModel):
    name: str
    slug: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    timezone: str = "Asia/Karachi"
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    is_main_branch: bool = False

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9\-]+$", v):
            raise ValueError("Slug may only contain lowercase letters, numbers, and hyphens")
        return v


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    is_main_branch: Optional[bool] = None
    is_active: Optional[bool] = None


class BranchResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    address: Optional[str]
    city: Optional[str]
    phone: Optional[str]
    timezone: Optional[str]
    bot_name: Optional[str]
    welcome_message: Optional[str]
    is_main_branch: bool
    is_active: bool

    model_config = {"from_attributes": True}


def _branch_response(b: Branch) -> BranchResponse:
    return BranchResponse(
        id=str(b.id),
        tenant_id=str(b.tenant_id),
        name=b.name,
        slug=b.slug,
        address=b.address,
        city=b.city,
        phone=b.phone,
        timezone=b.timezone,
        bot_name=b.bot_name,
        welcome_message=b.welcome_message,
        is_main_branch=b.is_main_branch,
        is_active=b.is_active,
    )


def _get_branch_or_404(branch_id: str, tenant_id, db: Session) -> Branch:
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.tenant_id == tenant_id,
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=List[BranchResponse])
def list_branches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all branches for the current user's tenant."""
    query = db.query(Branch).filter(Branch.tenant_id == current_user.tenant_id)
    # Branch-scoped users can only see their own branch
    if current_user.branch_id is not None:
        query = query.filter(Branch.id == current_user.branch_id)
    branches = query.order_by(Branch.is_main_branch.desc(), Branch.name).all()
    return [_branch_response(b) for b in branches]


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    data: BranchCreate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
):
    """Create a new branch. Tenant-level admin only (not branch admins)."""
    if data.is_main_branch:
        existing_main = db.query(Branch).filter(
            Branch.tenant_id == current_user.tenant_id,
            Branch.is_main_branch == True,
        ).first()
        if existing_main:
            raise HTTPException(
                status_code=400,
                detail=f"A main branch already exists: '{existing_main.name}'. Unset it first."
            )

    branch = Branch(
        tenant_id=current_user.tenant_id,
        name=data.name,
        slug=data.slug,
        address=data.address,
        city=data.city,
        phone=data.phone,
        timezone=data.timezone,
        bot_name=data.bot_name,
        welcome_message=data.welcome_message,
        is_main_branch=data.is_main_branch,
    )
    db.add(branch)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Branch slug is already taken")
    db.refresh(branch)
    return _branch_response(branch)


@router.get("/{branch_id}", response_model=BranchResponse)
def get_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single branch. Branch-scoped users may only fetch their own branch."""
    if current_user.branch_id is not None and str(current_user.branch_id) != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")
    branch = _get_branch_or_404(branch_id, current_user.tenant_id, db)
    return _branch_response(branch)


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: str,
    data: BranchUpdate,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Update branch details. Admin only."""
    branch = _get_branch_or_404(branch_id, current_user.tenant_id, db)

    if data.is_main_branch is True and not branch.is_main_branch:
        existing_main = db.query(Branch).filter(
            Branch.tenant_id == current_user.tenant_id,
            Branch.is_main_branch == True,
        ).first()
        if existing_main:
            raise HTTPException(
                status_code=400,
                detail=f"A main branch already exists: '{existing_main.name}'. Unset it first."
            )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)
    return _branch_response(branch)


@router.patch("/{branch_id}/toggle", response_model=BranchResponse)
def toggle_branch(
    branch_id: str,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
):
    """Toggle branch active/inactive. Tenant-level admin only."""
    branch = _get_branch_or_404(branch_id, current_user.tenant_id, db)

    if branch.is_active:
        active_count = db.query(Branch).filter(
            Branch.tenant_id == current_user.tenant_id,
            Branch.is_active == True,
        ).count()
        if active_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the last active branch"
            )

    branch.is_active = not branch.is_active
    db.commit()
    db.refresh(branch)
    return _branch_response(branch)
