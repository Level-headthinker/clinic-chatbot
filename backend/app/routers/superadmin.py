from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.chat import Lead, ChatSession
from app.services.auth import get_current_user

router = APIRouter(prefix="/super", tags=["Super Admin"])

def verify_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
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
    total_doctors = db.query(Doctor).filter(Doctor.is_active == True).count()
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

    appointment_counts = dict(
        db.query(Appointment.tenant_id, func.count(Appointment.id))
        .group_by(Appointment.tenant_id)
        .all()
    )
    lead_counts = dict(
        db.query(Lead.tenant_id, func.count(Lead.id))
        .group_by(Lead.tenant_id)
        .all()
    )
    doctor_counts = dict(
        db.query(Doctor.tenant_id, func.count(Doctor.id))
        .filter(Doctor.is_active == True)
        .group_by(Doctor.tenant_id)
        .all()
    )
    chat_counts = dict(
        db.query(ChatSession.tenant_id, func.count(ChatSession.id))
        .group_by(ChatSession.tenant_id)
        .all()
    )

    result = []
    for t in tenants:
        result.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "is_active": t.is_active,
            "created_at": str(t.created_at),
            "appointments": appointment_counts.get(t.id, 0),
            "leads": lead_counts.get(t.id, 0),
            "doctors": doctor_counts.get(t.id, 0),
            "chats": chat_counts.get(t.id, 0),
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
