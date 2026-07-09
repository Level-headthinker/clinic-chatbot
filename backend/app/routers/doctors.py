#  Admin endpoints to add, list, and update doctors.
# The clinic admin uses these from the dashboard to manage their doctors.
# The chatbot reads from these same records.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from app.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.auth import hash_password
from app.models.appointment import Appointment
from app.models.visit import VisitRecord


router = APIRouter(prefix="/doctors", tags=["Doctors"])


class DoctorCreate(BaseModel):
    name: str
    specialty: str
    qualification: Optional[str] = None
    bio: Optional[str] = None
    fee: Optional[str] = None
    available_slots: list = Field(default_factory=list)
    treatments: list = Field(default_factory=list)
    timings: list = Field(default_factory=list)
    slot_capacity: int = Field(default=1, ge=1, le=50)
    branch_id: Optional[str] = None


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    qualification: Optional[str] = None
    bio: Optional[str] = None
    fee: Optional[str] = None
    available_slots: Optional[list] = None
    treatments: Optional[list] = None
    timings: Optional[list] = None
    slot_capacity: Optional[int] = Field(default=None, ge=1, le=50)
    is_active: Optional[bool] = None


class DoctorLoginCreate(BaseModel):
    email: EmailStr
    password: str


@router.post("/")
def add_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    # Branch-scoped users are locked to their branch; tenant-level admins may specify one
    branch_id = current_user.branch_id or data.branch_id
    doctor = Doctor(
        tenant_id=current_user.tenant_id,
        branch_id=branch_id,
        name=data.name,
        specialty=data.specialty,
        qualification=data.qualification,
        bio=data.bio,
        fee=data.fee,
        available_slots=data.available_slots,
        treatments=data.treatments,
        timings=data.timings,
        slot_capacity=data.slot_capacity,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return {
        "message": "Doctor added successfully",
        "doctor_id": str(doctor.id)
    }


@router.get("/")
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    query = db.query(Doctor).filter(
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.is_active == True,
    )
    if current_user.branch_id is not None:
        query = query.filter(Doctor.branch_id == current_user.branch_id)
    doctors = query.all()

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "specialty": d.specialty,
            "qualification": d.qualification,
            "fee": d.fee,
            "available_slots": d.available_slots,
            "treatments": d.treatments or [],
            "timings": d.timings or [],
            "slot_capacity": d.slot_capacity or 1,
            "is_active": d.is_active,
            # FIX 4: Add tenant_id filter so counts are scoped to this clinic only.
            # Previously these counted records across ALL clinics.
            "total_visits": db.query(VisitRecord).filter(
                VisitRecord.doctor_id == d.id,
                VisitRecord.tenant_id == current_user.tenant_id,
            ).count(),
            "total_appointments": db.query(Appointment).filter(
                Appointment.doctor_id == d.id,
                Appointment.tenant_id == current_user.tenant_id,
            ).count(),
            "has_login": db.query(User).filter(User.doctor_id == d.id).first() is not None,
        }
        for d in doctors
    ]


@router.put("/{doctor_id}")
def update_doctor(
    doctor_id: str,
    data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.tenant_id == current_user.tenant_id
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if data.name is not None:
        doctor.name = data.name
    if data.specialty is not None:
        doctor.specialty = data.specialty
    if data.qualification is not None:
        doctor.qualification = data.qualification
    if data.bio is not None:
        doctor.bio = data.bio
    if data.fee is not None:
        doctor.fee = data.fee
    if data.slot_capacity is not None:
        doctor.slot_capacity = data.slot_capacity
    if data.is_active is not None:
        doctor.is_active = data.is_active

    if data.treatments is not None:
        doctor.treatments = list(data.treatments)
    if data.timings is not None:
        doctor.timings = [dict(t) for t in data.timings]

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(doctor, "treatments")
    flag_modified(doctor, "timings")

    db.commit()
    db.refresh(doctor)
    return {"message": "Doctor updated successfully"}


@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.tenant_id == current_user.tenant_id
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.is_active = False
    db.commit()
    return {"message": "Doctor removed successfully"}


@router.post("/{doctor_id}/create-login")
def create_doctor_login(
    doctor_id: str,
    data: DoctorLoginCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.tenant_id == current_user.tenant_id,
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if db.query(User).filter(User.doctor_id == doctor.id).first():
        raise HTTPException(status_code=400, detail="This doctor already has a login")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already in use")

    user = User(
        tenant_id=current_user.tenant_id,
        branch_id=doctor.branch_id,
        doctor_id=doctor.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=doctor.name,
        role="doctor",
    )
    db.add(user)
    db.commit()
    return {"message": "Doctor login created successfully"}
