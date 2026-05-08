from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.patient import Patient
from app.models.visit import VisitRecord
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/patients", tags=["Patients"])


class PatientCreate(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact: Optional[str] = None


@router.post("/")
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Patient).filter(
        Patient.phone == data.phone,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone already exists"
        )

    patient = Patient(
        tenant_id=current_user.tenant_id,
        name=data.name,
        phone=data.phone,
        age=data.age,
        gender=data.gender,
        blood_group=data.blood_group,
        allergies=data.allergies,
        chronic_conditions=data.chronic_conditions,
        emergency_contact=data.emergency_contact
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {
        "message": "Patient created successfully",
        "patient_id": str(patient.id)
    }


@router.get("/")
def list_patients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Patient).filter(
        Patient.tenant_id == current_user.tenant_id,
        Patient.is_active == True
    )
    if search:
        query = query.filter(
            (Patient.name.ilike(f"%{search}%")) |
            (Patient.phone.ilike(f"%{search}%"))
        )
    patients = query.order_by(Patient.created_at.desc()).all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "phone": p.phone,
            "age": p.age,
            "gender": p.gender,
            "blood_group": p.blood_group,
            "allergies": p.allergies,
            "chronic_conditions": p.chronic_conditions,
            "emergency_contact": p.emergency_contact,
            "total_visits": len(p.visit_records),
            "created_at": str(p.created_at)
        }
        for p in patients
    ]


@router.get("/lookup/{phone}")
def lookup_patient(
    phone: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.phone == phone,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = db.query(VisitRecord).filter(
        VisitRecord.patient_id == patient.id
    ).order_by(VisitRecord.visit_date.desc()).all()

    return {
        "id": str(patient.id),
        "name": patient.name,
        "phone": patient.phone,
        "age": patient.age,
        "gender": patient.gender,
        "blood_group": patient.blood_group,
        "allergies": patient.allergies,
        "chronic_conditions": patient.chronic_conditions,
        "emergency_contact": patient.emergency_contact,
        "total_visits": len(visits),
        "last_visit": str(visits[0].visit_date) if visits else None,
        "visits": [
            {
                "id": str(v.id),
                "visit_date": str(v.visit_date),
                "complaint": v.complaint,
                "diagnosis": v.diagnosis,
                "prescription": v.prescription,
                "tests_ordered": v.tests_ordered,
                "next_visit_date": str(v.next_visit_date) if v.next_visit_date else None,
                "fee": v.fee,
                "doctor_name": v.doctor.name if v.doctor else "Unknown"
            }
            for v in visits
        ]
    }


@router.get("/{patient_id}")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = db.query(VisitRecord).filter(
        VisitRecord.patient_id == patient.id
    ).order_by(VisitRecord.visit_date.desc()).all()

    return {
        "id": str(patient.id),
        "name": patient.name,
        "phone": patient.phone,
        "age": patient.age,
        "gender": patient.gender,
        "blood_group": patient.blood_group,
        "allergies": patient.allergies,
        "chronic_conditions": patient.chronic_conditions,
        "emergency_contact": patient.emergency_contact,
        "total_visits": len(visits),
        "last_visit": str(visits[0].visit_date) if visits else None,
        "visits": [
            {
                "id": str(v.id),
                "visit_date": str(v.visit_date),
                "complaint": v.complaint,
                "diagnosis": v.diagnosis,
                "prescription": v.prescription,
                "tests_ordered": v.tests_ordered,
                "test_results": v.test_results,
                "doctor_notes": v.doctor_notes,
                "next_visit_date": str(v.next_visit_date) if v.next_visit_date else None,
                "fee": v.fee,
                "doctor_name": v.doctor.name if v.doctor else "Unknown"
            }
            for v in visits
        ]
    }


@router.put("/{patient_id}")
def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if data.name is not None: patient.name = data.name
    if data.age is not None: patient.age = data.age
    if data.gender is not None: patient.gender = data.gender
    if data.blood_group is not None: patient.blood_group = data.blood_group
    if data.allergies is not None: patient.allergies = data.allergies
    if data.chronic_conditions is not None: patient.chronic_conditions = data.chronic_conditions
    if data.emergency_contact is not None: patient.emergency_contact = data.emergency_contact

    db.commit()
    return {"message": "Patient updated successfully"}


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.is_active = False
    db.commit()
    return {"message": "Patient removed"}