#  Admin endpoints to add, list, and update doctors.
# The clinic admin uses these from the dashboard to manage their doctors.
# The chatbot reads from these same records.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/doctors", tags=["Doctors"])


class DoctorCreate(BaseModel):
    name: str
    specialty: str
    qualification: Optional[str] = None
    bio: Optional[str] = None
    fee: Optional[str] = None
    available_slots: Optional[list] = []
    treatments: Optional[list] = []
    timings: Optional[list] = []


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    qualification: Optional[str] = None
    bio: Optional[str] = None
    fee: Optional[str] = None
    available_slots: Optional[list] = None
    treatments: Optional[list] = None
    timings: Optional[list] = None
    is_active: Optional[bool] = None


@router.post("/")
def add_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = Doctor(
        tenant_id=current_user.tenant_id,
        name=data.name,
        specialty=data.specialty,
        qualification=data.qualification,
        bio=data.bio,
        fee=data.fee,
        available_slots=data.available_slots,
        treatments=data.treatments,
        timings=data.timings
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
    current_user: User = Depends(get_current_user)
):
    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == current_user.tenant_id
    ).all()
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
            "is_active": d.is_active
        }
        for d in doctors
    ]


@router.put("/{doctor_id}")
def update_doctor(
    doctor_id: str,
    data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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