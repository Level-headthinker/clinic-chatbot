from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import VisitRecord
from app.models.user import User
from app.services.auth import require_doctor_user

router = APIRouter(prefix="/doctor", tags=["Doctor Portal"])


def _now():
    return datetime.now(timezone.utc)


@router.get("/me")
def doctor_me(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == current_user.doctor_id).first()
    if not doctor:
        return {}
    return {
        "id": str(doctor.id),
        "name": doctor.name,
        "specialty": doctor.specialty,
        "qualification": doctor.qualification,
        "fee": doctor.fee,
        "bio": doctor.bio,
        "timings": doctor.timings or [],
        "treatments": doctor.treatments or [],
    }


@router.get("/stats")
def doctor_stats(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    doctor_id = current_user.doctor_id

    total_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.is_active == True,
    ).count()

    today_count = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.is_active == True,
        Appointment.slot_datetime >= today_start,
        Appointment.slot_datetime < today_end,
        Appointment.status.in_(["pending", "confirmed"]),
    ).count()

    total_visits = db.query(VisitRecord).filter(
        VisitRecord.doctor_id == doctor_id,
        VisitRecord.is_active == True,
    ).count()

    total_patients = db.query(VisitRecord.patient_id).filter(
        VisitRecord.doctor_id == doctor_id,
        VisitRecord.is_active == True,
    ).distinct().count()

    return {
        "total_appointments": total_appointments,
        "today_appointments": today_count,
        "total_visits": total_visits,
        "total_patients": total_patients,
    }


@router.get("/schedule")
def doctor_schedule(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.is_active == True,
            Appointment.slot_datetime >= today_start,
            Appointment.slot_datetime < week_end,
        )
        .order_by(Appointment.slot_datetime.asc())
        .all()
    )

    today_str = today_start.date().isoformat()
    today_appts = []
    upcoming_appts = []

    for a in appointments:
        slot_date = a.slot_datetime.date().isoformat() if a.slot_datetime else None
        row = {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "patient_concern": a.patient_concern,
            "slot_datetime": a.slot_datetime.isoformat() if a.slot_datetime else None,
            "status": a.status,
        }
        if slot_date == today_str:
            today_appts.append(row)
        else:
            upcoming_appts.append(row)

    return {"today": today_appts, "upcoming": upcoming_appts}


@router.get("/patients")
def doctor_patients(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    visits = (
        db.query(VisitRecord)
        .options(joinedload(VisitRecord.patient))
        .filter(
            VisitRecord.doctor_id == current_user.doctor_id,
            VisitRecord.is_active == True,
        )
        .order_by(VisitRecord.visit_date.desc())
        .all()
    )

    seen = set()
    patients = []
    for v in visits:
        if not v.patient or str(v.patient_id) in seen:
            continue
        seen.add(str(v.patient_id))
        patients.append({
            "id": str(v.patient.id),
            "name": v.patient.name,
            "phone": v.patient.phone,
            "last_visit": v.visit_date.isoformat() if v.visit_date else None,
            "complaint": v.complaint,
            "diagnosis": v.diagnosis,
        })

    return patients
