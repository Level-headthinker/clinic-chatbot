from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.treatment_course import TreatmentCourse
from app.models.patient import Patient
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/courses", tags=["Treatment Courses"])


class CourseCreate(BaseModel):
    patient_id: str
    service_name: str
    total_sessions: int
    price_per_course: Optional[float] = None
    notes: Optional[str] = None


def _fmt(c: TreatmentCourse) -> dict:
    return {
        "id": str(c.id),
        "patient_id": str(c.patient_id),
        "service_name": c.service_name,
        "total_sessions": c.total_sessions,
        "completed_sessions": c.completed_sessions,
        "remaining_sessions": max(0, c.total_sessions - c.completed_sessions),
        "price_per_course": float(c.price_per_course) if c.price_per_course else None,
        "status": c.status,
        "notes": c.notes,
        "created_at": str(c.created_at),
    }


@router.get("/")
def list_courses(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    courses = (
        db.query(TreatmentCourse)
        .filter(
            TreatmentCourse.patient_id == patient_id,
            TreatmentCourse.tenant_id == current_user.tenant_id,
        )
        .order_by(TreatmentCourse.created_at.desc())
        .all()
    )
    return [_fmt(c) for c in courses]


@router.post("/")
def create_course(
    data: CourseCreate,
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

    course = TreatmentCourse(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        patient_id=data.patient_id,
        patient_phone=patient.phone,
        service_name=data.service_name,
        total_sessions=data.total_sessions,
        price_per_course=data.price_per_course,
        notes=data.notes,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _fmt(course)


@router.post("/{course_id}/session")
def complete_session(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.query(TreatmentCourse).filter(
        TreatmentCourse.id == course_id,
        TreatmentCourse.tenant_id == current_user.tenant_id,
    ).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.status != "active":
        raise HTTPException(400, "Course is not active")
    if course.completed_sessions >= course.total_sessions:
        raise HTTPException(400, "All sessions already completed")

    course.completed_sessions += 1
    if course.completed_sessions >= course.total_sessions:
        course.status = "completed"

    db.commit()
    db.refresh(course)
    return _fmt(course)


@router.delete("/{course_id}")
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.query(TreatmentCourse).filter(
        TreatmentCourse.id == course_id,
        TreatmentCourse.tenant_id == current_user.tenant_id,
    ).first()
    if not course:
        raise HTTPException(404, "Course not found")
    db.delete(course)
    db.commit()
    return {"message": "Course deleted"}
