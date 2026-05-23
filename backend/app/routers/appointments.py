# Handles booking appointments. Two types of users hit these endpoints
#  — the chatbot books on behalf of patients,
#  and the admin manages bookings from the dashboard.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.messaging import send_whatsapp

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
    current_user: User = Depends(require_admin_user)
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
        branch_id=current_user.branch_id or doctor.branch_id,
        doctor_id=data.doctor_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        patient_concern=data.patient_concern,
        slot_datetime=data.slot_datetime,
        status="pending"
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="This slot is already booked"
        )
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
    current_user: User = Depends(require_admin_user)
):
    query = db.query(Appointment).options(
        joinedload(Appointment.doctor)
    ).filter(
        Appointment.tenant_id == current_user.tenant_id,
        Appointment.is_active == True,
    )
    if current_user.branch_id is not None:
        query = query.filter(Appointment.branch_id == current_user.branch_id)
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
            "reminder_sent": a.reminder_sent,
            "created_at": str(a.created_at)
        }
        for a in appointments
    ]


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
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


@router.post("/{appointment_id}/remind")
def send_reminder(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()

    clinic_name = tenant.name if tenant else "the clinic"
    doctor_name = doctor.name if doctor else "your doctor"
    if doctor_name and not doctor_name.lower().startswith("dr"):
        doctor_name = f"Dr. {doctor_name}"

    slot_str = appointment.slot_datetime.strftime("%A, %d %B at %I:%M %p")
    message = (
        f"Hi {appointment.patient_name}! 👋\n\n"
        f"This is a reminder from {clinic_name}.\n"
        f"Your appointment with {doctor_name} is scheduled for:\n"
        f"📅 {slot_str}\n\n"
        f"Please arrive 10 minutes early. "
        f"To reschedule, reply to this message or call us directly."
    )

    sent = send_whatsapp(appointment.patient_phone, message)
    if not sent:
        raise HTTPException(status_code=503, detail="WhatsApp not configured. Add META credentials in .env.")

    appointment.reminder_sent = True
    db.commit()
    return {"message": "Reminder sent successfully."}


@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
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
