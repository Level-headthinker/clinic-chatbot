from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.prescription import Prescription
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


class MedicationItem(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    notes: Optional[str] = None


class PrescriptionCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    diagnosis: Optional[str] = None
    medications: List[MedicationItem] = []
    instructions: Optional[str] = None


class PrescriptionUpdate(BaseModel):
    diagnosis: Optional[str] = None
    medications: Optional[List[MedicationItem]] = None
    instructions: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: Optional[str]
    doctor_id: Optional[str]
    diagnosis: Optional[str]
    medications: List[Any]
    instructions: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


def _fmt(p: Prescription) -> PrescriptionResponse:
    return PrescriptionResponse(
        id=str(p.id),
        patient_id=str(p.patient_id),
        appointment_id=str(p.appointment_id) if p.appointment_id else None,
        doctor_id=str(p.doctor_id) if p.doctor_id else None,
        diagnosis=p.diagnosis,
        medications=p.medications or [],
        instructions=p.instructions,
        created_by=str(p.created_by) if p.created_by else None,
        created_at=p.created_at,
    )


def _base_query(current_user: User, db: Session):
    q = db.query(Prescription).filter(Prescription.tenant_id == current_user.tenant_id)
    if current_user.branch_id:
        q = q.filter(Prescription.branch_id == current_user.branch_id)
    return q


@router.get("", response_model=List[PrescriptionResponse])
def list_prescriptions(
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _base_query(current_user, db)
    if patient_id:
        q = q.filter(Prescription.patient_id == patient_id)
    return [_fmt(p) for p in q.order_by(Prescription.created_at.desc()).all()]


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    data: PrescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rx = Prescription(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        patient_id=data.patient_id,
        appointment_id=data.appointment_id or None,
        doctor_id=data.doctor_id or None,
        created_by=current_user.id,
        diagnosis=data.diagnosis,
        medications=[m.model_dump() for m in data.medications],
        instructions=data.instructions,
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)
    return _fmt(rx)


@router.put("/{rx_id}", response_model=PrescriptionResponse)
def update_prescription(
    rx_id: str,
    data: PrescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rx = _base_query(current_user, db).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if data.diagnosis is not None:
        rx.diagnosis = data.diagnosis
    if data.instructions is not None:
        rx.instructions = data.instructions
    if data.medications is not None:
        rx.medications = [m.model_dump() for m in data.medications]
    db.commit()
    db.refresh(rx)
    return _fmt(rx)


@router.delete("/{rx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    rx_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rx = _base_query(current_user, db).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    db.delete(rx)
    db.commit()
