from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.service import Service
from app.models.user import User
from app.services.auth import require_admin_user

router = APIRouter(prefix="/services", tags=["Services"])


class ServiceCreate(BaseModel):
    name: str
    duration_minutes: Optional[int] = 30
    price: Optional[float] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


def _fmt(s):
    return {
        "id": str(s.id),
        "name": s.name,
        "duration_minutes": s.duration_minutes,
        "price": float(s.price) if s.price is not None else None,
        "is_active": s.is_active,
        "created_at": str(s.created_at),
    }


@router.get("/")
def list_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    q = db.query(Service).filter(
        Service.tenant_id == current_user.tenant_id,
        Service.is_active == True,
    )
    if current_user.branch_id:
        q = q.filter(Service.branch_id == current_user.branch_id)
    return [_fmt(s) for s in q.order_by(Service.name).all()]


@router.post("/")
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    svc = Service(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        name=data.name.strip(),
        duration_minutes=data.duration_minutes,
        price=data.price,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return _fmt(svc)


@router.put("/{service_id}")
def update_service(
    service_id: str,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    svc = db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == current_user.tenant_id,
    ).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    if data.name is not None:
        svc.name = data.name.strip()
    if data.duration_minutes is not None:
        svc.duration_minutes = data.duration_minutes
    if data.price is not None:
        svc.price = data.price
    if data.is_active is not None:
        svc.is_active = data.is_active
    db.commit()
    return _fmt(svc)


@router.delete("/{service_id}")
def delete_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    svc = db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == current_user.tenant_id,
    ).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    svc.is_active = False
    db.commit()
    return {"message": "Service removed."}
