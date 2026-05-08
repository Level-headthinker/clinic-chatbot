from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.chat import Lead, ChatSession
from app.services.auth import get_current_user

router = APIRouter(prefix="/super", tags=["Super Admin"])

SUPER_ADMIN_EMAIL = "admin@cityclinic.com"

def verify_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.email != SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    total_appointments = db.query(Appointment).count()
    total_leads = db.query(Lead).count()
    total_doctors = db.query(Doctor).filter(
    Doctor.is_active == True
).count()
    total_chats = db.query(ChatSession).count()

    return {
        "total_clinics": total_tenants,
        "total_appointments": total_appointments,
        "total_leads": total_leads,
        "total_doctors": total_doctors,
        "total_chats": total_chats,
        "estimated_mrr": total_tenants * 3000,
        "estimated_arr": total_tenants * 3000 * 12,
    }


@router.get("/clinics")
def get_all_clinics(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    result = []
    for t in tenants:
        appointments = db.query(Appointment).filter(
            Appointment.tenant_id == t.id
        ).count()
        leads = db.query(Lead).filter(
            Lead.tenant_id == t.id
        ).count()
        doctors = db.query(Doctor).filter(
            Doctor.tenant_id == t.id,
            Doctor.is_active == True
        ).count()
        chats = db.query(ChatSession).filter(
            ChatSession.tenant_id == t.id
        ).count()
        result.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "is_active": t.is_active,
            "created_at": str(t.created_at),
            "appointments": appointments,
            "leads": leads,
            "doctors": doctors,
            "chats": chats,
        })
    return result


@router.put("/clinics/{tenant_id}/toggle")
def toggle_clinic(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    tenant.is_active = not tenant.is_active
    db.commit()
    return {
        "message": f"Clinic {'activated' if tenant.is_active else 'deactivated'}",
        "is_active": tenant.is_active
    }


@router.put("/clinics/{tenant_id}/plan")
def update_plan(
    tenant_id: str,
    plan: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    allowed = ["starter", "growth", "enterprise"]
    if plan not in allowed:
        raise HTTPException(status_code=400, detail=f"Plan must be one of {allowed}")
    tenant.plan = plan
    db.commit()
    return {"message": "Plan updated", "plan": plan}