from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from app.database import get_db
from app.models.visit import VisitRecord
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.invoice import Invoice
from app.models.user import User
from app.services.auth import get_current_user
from app.services.invoices import generate_invoice_number

router = APIRouter(prefix="/visits", tags=["Visits"])


class PrescriptionItem(BaseModel):
    medicine: str
    dosage: str
    frequency: str
    duration: str
    notes: Optional[str] = None


class VisitCreate(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: List[PrescriptionItem] = Field(default_factory=list)
    tests_ordered: Optional[str] = None
    test_results: Optional[str] = None
    doctor_notes: Optional[str] = None
    next_visit_date: Optional[date] = None
    fee: Optional[int] = 0


class VisitUpdate(BaseModel):
    complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[List[PrescriptionItem]] = None
    tests_ordered: Optional[str] = None
    test_results: Optional[str] = None
    doctor_notes: Optional[str] = None
    next_visit_date: Optional[date] = None
    fee: Optional[int] = None


@router.post("/")
def create_visit(
    data: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify patient belongs to this clinic
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # FIX 2: Verify doctor_id belongs to THIS clinic before assigning.
    # Previously, any doctor_id from any clinic could be submitted.
    if data.doctor_id:
        doctor = db.query(Doctor).filter(
            Doctor.id == data.doctor_id,
            Doctor.tenant_id == current_user.tenant_id   # ← enforces ownership
        ).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

    visit = VisitRecord(
        tenant_id=current_user.tenant_id,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        complaint=data.complaint,
        diagnosis=data.diagnosis,
        prescription=[p.dict() for p in data.prescription] if data.prescription else [],
        tests_ordered=data.tests_ordered,
        test_results=data.test_results,
        doctor_notes=data.doctor_notes,
        next_visit_date=data.next_visit_date,
        fee=data.fee or 0
    )
    db.add(visit)
    db.flush()

    if data.fee and data.fee > 0:
        invoice = Invoice(
            tenant_id=current_user.tenant_id,
            patient_id=data.patient_id,
            visit_id=visit.id,
            invoice_number=generate_invoice_number(current_user.tenant_id),
            consultation_fee=data.fee,
            additional_charges=[],
            total_amount=data.fee,
            paid_amount=0,
            payment_status="unpaid"
        )
        db.add(invoice)

    db.commit()
    db.refresh(visit)

    return {
        "message": "Visit recorded successfully",
        "visit_id": str(visit.id),
        "invoice_created": data.fee and data.fee > 0
    }


@router.get("/patient/{patient_id}")
def get_patient_visits(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify patient belongs to this clinic first
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = db.query(VisitRecord).filter(
        VisitRecord.patient_id == patient_id,
        VisitRecord.tenant_id == current_user.tenant_id,   # ← added for defence-in-depth
        VisitRecord.is_active == True
    ).order_by(VisitRecord.visit_date.desc()).all()

    return [
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


@router.get("/{visit_id}")
def get_visit(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = db.query(VisitRecord).filter(
        VisitRecord.id == visit_id,
        VisitRecord.tenant_id == current_user.tenant_id
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    return {
        "id": str(visit.id),
        "patient_name": visit.patient.name,
        "patient_phone": visit.patient.phone,
        "visit_date": str(visit.visit_date),
        "complaint": visit.complaint,
        "diagnosis": visit.diagnosis,
        "prescription": visit.prescription,
        "tests_ordered": visit.tests_ordered,
        "test_results": visit.test_results,
        "doctor_notes": visit.doctor_notes,
        "next_visit_date": str(visit.next_visit_date) if visit.next_visit_date else None,
        "fee": visit.fee,
        "doctor_name": visit.doctor.name if visit.doctor else "Unknown"
    }


@router.put("/{visit_id}")
def update_visit(
    visit_id: str,
    data: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visit = db.query(VisitRecord).filter(
        VisitRecord.id == visit_id,
        VisitRecord.tenant_id == current_user.tenant_id
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if data.complaint is not None: visit.complaint = data.complaint
    if data.diagnosis is not None: visit.diagnosis = data.diagnosis
    if data.prescription is not None:
        visit.prescription = [p.dict() for p in data.prescription]
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(visit, "prescription")
    if data.tests_ordered is not None: visit.tests_ordered = data.tests_ordered
    if data.test_results is not None: visit.test_results = data.test_results
    if data.doctor_notes is not None: visit.doctor_notes = data.doctor_notes
    if data.next_visit_date is not None: visit.next_visit_date = data.next_visit_date
    if data.fee is not None:
        visit.fee = data.fee
        # FIX 5: Add tenant_id filter so we only touch invoices that belong to this clinic
        existing_invoice = db.query(Invoice).filter(
            Invoice.visit_id == visit.id,
            Invoice.tenant_id == current_user.tenant_id   # ← added
        ).first()
        if existing_invoice:
            existing_invoice.consultation_fee = data.fee
            existing_invoice.total_amount = data.fee + sum(
                c.get("amount", 0)
                for c in (existing_invoice.additional_charges or [])
            )

    db.commit()
    return {"message": "Visit updated successfully"}