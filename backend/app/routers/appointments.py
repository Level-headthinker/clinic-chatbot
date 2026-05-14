# Handles booking appointments. Two types of users hit these endpoints
#  — the chatbot books on behalf of patients,
#  and the admin manages bookings from the dashboard.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class AppointmentCreate(BaseModel):
    doctor_id: str
    patient_name: str
    patient_phone: str
    patient_concern: Optional[str] = None
    slot_datetime: datetime


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/book")
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(Doctor).filter(
        Doctor.id == data.doctor_id,
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    existing = db.query(Appointment).filter(
        Appointment.doctor_id == data.doctor_id,
        Appointment.tenant_id == current_user.tenant_id,
        Appointment.slot_datetime == data.slot_datetime,
        Appointment.status.in_(["pending", "confirmed"])
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This slot is already booked"
        )

    appointment = Appointment(
        tenant_id=current_user.tenant_id,
        doctor_id=data.doctor_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        patient_concern=data.patient_concern,
        slot_datetime=data.slot_datetime,
        status="pending"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment booked successfully",
        "appointment_id": str(appointment.id),
        "status": appointment.status,
        "slot": str(appointment.slot_datetime)
    }


@router.get("/")
def list_appointments(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Appointment).filter(
        Appointment.tenant_id == current_user.tenant_id,
        Appointment.is_active == True
    )
    if status:
        query = query.filter(Appointment.status == status)

    appointments = query.order_by(
        Appointment.slot_datetime.asc()
    ).all()

    return [
        {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "patient_concern": a.patient_concern,
            "doctor_id": str(a.doctor_id),
            "doctor_name": a.doctor.name,
            "doctor_specialty": a.doctor.specialty,
            "doctor_fee": a.doctor.fee,
            "slot_datetime": str(a.slot_datetime),
            "status": a.status,
            "notes": a.notes,
            "created_at": str(a.created_at)
        }
        for a in appointments
    ]


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id
    ).first()
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    if data.status is not None:
        allowed = ["pending", "confirmed", "cancelled", "completed", "no_show"]
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of {allowed}"
            )
        appointment.status = data.status
    if data.notes is not None:
        appointment.notes = data.notes

    db.commit()
    return {"message": "Appointment updated successfully"}


@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id
    ).first()
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    appointment.status = "cancelled"
    db.commit()
    return {"message": "Appointment cancelled"}
