from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models.patient import Patient
from app.models.visit import VisitRecord
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.audit import log_audit, snapshot

# Fields captured in audit snapshots for a patient.
_PATIENT_FIELDS = [
    "name", "phone", "age", "gender", "blood_group",
    "allergies", "chronic_conditions", "emergency_contact",
]

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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
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
    db.flush()
    log_audit(
        db, tenant_id=current_user.tenant_id, action="create",
        entity_type="patient", entity_id=patient.id,
        summary=f"Created patient {patient.name}",
        after=snapshot(patient, _PATIENT_FIELDS),
        user=current_user, request=request,
    )
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
    current_user: User = Depends(require_admin_user)
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
    if not patients:
        return []

    visit_counts = dict(
        db.query(VisitRecord.patient_id, func.count(VisitRecord.id))
        .filter(VisitRecord.tenant_id == current_user.tenant_id)
        .group_by(VisitRecord.patient_id)
        .all()
    )

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
            "total_visits": visit_counts.get(p.id, 0),
            "created_at": str(p.created_at)
        }
        for p in patients
    ]


@router.get("/lookup/{phone}")
def lookup_patient(
    phone: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    patient = db.query(Patient).filter(
        Patient.phone == phone,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = db.query(VisitRecord).filter(
        VisitRecord.patient_id == patient.id,
        VisitRecord.tenant_id == current_user.tenant_id
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
    current_user: User = Depends(require_admin_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = db.query(VisitRecord).filter(
        VisitRecord.patient_id == patient.id,
        VisitRecord.tenant_id == current_user.tenant_id
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    before = snapshot(patient, _PATIENT_FIELDS)
    if data.name is not None: patient.name = data.name
    if data.age is not None: patient.age = data.age
    if data.gender is not None: patient.gender = data.gender
    if data.blood_group is not None: patient.blood_group = data.blood_group
    if data.allergies is not None: patient.allergies = data.allergies
    if data.chronic_conditions is not None: patient.chronic_conditions = data.chronic_conditions
    if data.emergency_contact is not None: patient.emergency_contact = data.emergency_contact

    # Only record the fields that actually changed.
    after = snapshot(patient, _PATIENT_FIELDS)
    changed_before = {k: v for k, v in before.items() if before[k] != after[k]}
    changed_after = {k: v for k, v in after.items() if before[k] != after[k]}
    if changed_after:
        log_audit(
            db, tenant_id=current_user.tenant_id, action="update",
            entity_type="patient", entity_id=patient.id,
            summary=f"Updated patient {patient.name}",
            before=changed_before, after=changed_after,
            user=current_user, request=request,
        )
    db.commit()
    return {"message": "Patient updated successfully"}


@router.get("/trash/list")
def list_deleted_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Soft-deleted patients (the 'trash bin') — recoverable via restore."""
    patients = db.query(Patient).filter(
        Patient.tenant_id == current_user.tenant_id,
        Patient.is_active == False,
    ).order_by(Patient.deleted_at.desc().nullslast()).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "phone": p.phone,
            "deleted_at": str(p.deleted_at) if p.deleted_at else None,
        }
        for p in patients
    ]


@router.post("/{patient_id}/restore")
def restore_patient(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Bring a soft-deleted patient back. Recovers accidental deletes without
    touching backups."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id,
        Patient.is_active == False,
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Deleted patient not found")

    patient.is_active = True
    patient.deleted_at = None
    log_audit(
        db, tenant_id=current_user.tenant_id, action="restore",
        entity_type="patient", entity_id=patient.id,
        summary=f"Restored patient {patient.name}",
        user=current_user, request=request,
    )
    db.commit()
    return {"message": "Patient restored"}


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.is_active = False
    patient.deleted_at = datetime.now(timezone.utc)
    log_audit(
        db, tenant_id=current_user.tenant_id, action="delete",
        entity_type="patient", entity_id=patient.id,
        summary=f"Deleted patient {patient.name}",
        before=snapshot(patient, _PATIENT_FIELDS),
        user=current_user, request=request,
    )
    db.commit()
    return {"message": "Patient removed"}
