from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.treatment_session import TreatmentSession
from app.models.patient import Patient
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/sessions", tags=["Treatment Sessions"])


class SessionCreate(BaseModel):
    patient_id: str
    service_name: str
    total_sessions: int
    price_per_session: Optional[float] = None
    notes: Optional[str] = None


def _fmt(s: TreatmentSession) -> dict:
    pps = float(s.price_per_session) if s.price_per_session else None
    return {
        "id": str(s.id),
        "patient_id": str(s.patient_id),
        "service_name": s.service_name,
        "total_sessions": s.total_sessions,
        "completed_sessions": s.completed_sessions,
        "remaining_sessions": max(0, s.total_sessions - s.completed_sessions),
        "price_per_session": pps,
        "total_price": round(pps * s.total_sessions, 2) if pps else None,
        "billed_so_far": round(pps * s.completed_sessions, 2) if pps else None,
        "status": s.status,
        "notes": s.notes,
        "created_at": str(s.created_at),
    }


@router.get("/")
def list_sessions(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(TreatmentSession)
        .filter(
            TreatmentSession.patient_id == patient_id,
            TreatmentSession.tenant_id == current_user.tenant_id,
        )
        .order_by(TreatmentSession.created_at.desc())
        .all()
    )
    return [_fmt(s) for s in sessions]


@router.post("/")
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.tenant_id == current_user.tenant_id,
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    if not 1 <= data.total_sessions <= 100:
        raise HTTPException(400, "Sessions must be between 1 and 100")

    session = TreatmentSession(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        patient_id=data.patient_id,
        patient_phone=patient.phone,
        service_name=data.service_name,
        total_sessions=data.total_sessions,
        price_per_session=data.price_per_session,
        notes=data.notes,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _fmt(session)


@router.post("/{session_id}/complete")
def complete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(TreatmentSession).filter(
        TreatmentSession.id == session_id,
        TreatmentSession.tenant_id == current_user.tenant_id,
    ).first()
    if not session:
        raise HTTPException(404, "Session package not found")
    if session.status != "active":
        raise HTTPException(400, "Session package is not active")
    if session.completed_sessions >= session.total_sessions:
        raise HTTPException(400, "All sessions already completed")

    session.completed_sessions += 1
    if session.completed_sessions >= session.total_sessions:
        session.status = "completed"

    db.commit()
    db.refresh(session)
    return _fmt(session)


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(TreatmentSession).filter(
        TreatmentSession.id == session_id,
        TreatmentSession.tenant_id == current_user.tenant_id,
    ).first()
    if not session:
        raise HTTPException(404, "Session package not found")
    db.delete(session)
    db.commit()
    return {"message": "Deleted"}
