from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.database import get_db
from app.models.invoice import Invoice
from app.models.patient import Patient
from app.models.visit import VisitRecord
from app.models.user import User
from app.services.auth import get_current_user
from app.services.invoices import generate_invoice_number

router = APIRouter(prefix="/billing", tags=["Billing"])


class AdditionalCharge(BaseModel):
    description: str
    amount: int


class InvoiceCreate(BaseModel):
    patient_id: str
    visit_id: Optional[str] = None
    consultation_fee: int = 0
    additional_charges: List[AdditionalCharge] = Field(default_factory=list)
    payment_status: Optional[str] = "unpaid"
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    paid_amount: int
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None


class AddCharge(BaseModel):
    description: str
    amount: int


@router.post("/")
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.tenant_id == current_user.tenant_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    additional_total = sum(
        c.amount for c in data.additional_charges
    ) if data.additional_charges else 0
    total = data.consultation_fee + additional_total

    invoice = Invoice(
        tenant_id=current_user.tenant_id,
        patient_id=data.patient_id,
        visit_id=data.visit_id,
        invoice_number=generate_invoice_number(current_user.tenant_id),
        consultation_fee=data.consultation_fee,
        additional_charges=[c.dict() for c in data.additional_charges] if data.additional_charges else [],
        total_amount=total,
        paid_amount=total if data.payment_status == "paid" else 0,
        payment_status=data.payment_status or "unpaid",
        payment_method=data.payment_method,
        notes=data.notes
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "message": "Invoice created",
        "invoice_id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "total_amount": total
    }


@router.get("/")
def list_invoices(
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Invoice).filter(
        Invoice.tenant_id == current_user.tenant_id,
        Invoice.is_active == True
    )
    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status)

    invoices = query.order_by(Invoice.created_at.desc()).all()

    return [
        {
            "id": str(i.id),
            "invoice_number": i.invoice_number,
            "patient_name": i.patient.name,
            "patient_phone": i.patient.phone,
            "consultation_fee": i.consultation_fee,
            "additional_charges": i.additional_charges,
            "total_amount": i.total_amount,
            "paid_amount": i.paid_amount,
            "balance": i.total_amount - i.paid_amount,
            "payment_status": i.payment_status,
            "payment_method": i.payment_method,
            "notes": i.notes,
            "created_at": str(i.created_at)
        }
        for i in invoices
    ]


@router.get("/stats")
def billing_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()

    total_revenue = db.query(
        func.sum(Invoice.paid_amount)
    ).filter(
        Invoice.tenant_id == current_user.tenant_id
    ).scalar() or 0

    pending_amount = db.query(
        func.sum(Invoice.total_amount - Invoice.paid_amount)
    ).filter(
        Invoice.tenant_id == current_user.tenant_id,
        Invoice.payment_status != "paid"
    ).scalar() or 0

    today_revenue = db.query(
        func.sum(Invoice.paid_amount)
    ).filter(
        Invoice.tenant_id == current_user.tenant_id,
        func.date(Invoice.created_at) == today
    ).scalar() or 0

    today_invoices = db.query(Invoice).filter(
        Invoice.tenant_id == current_user.tenant_id,
        func.date(Invoice.created_at) == today
    ).count()

    total_invoices = db.query(Invoice).filter(
        Invoice.tenant_id == current_user.tenant_id
    ).count()

    paid_invoices = db.query(Invoice).filter(
        Invoice.tenant_id == current_user.tenant_id,
        Invoice.payment_status == "paid"
    ).count()

    return {
        "total_revenue": total_revenue,
        "pending_amount": pending_amount,
        "today_revenue": today_revenue,
        "today_invoices": today_invoices,
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "unpaid_invoices": total_invoices - paid_invoices,
        "collection_rate": f"{(paid_invoices / total_invoices * 100):.1f}%" if total_invoices > 0 else "0%"
    }


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == current_user.tenant_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "patient_name": invoice.patient.name,
        "patient_phone": invoice.patient.phone,
        "consultation_fee": invoice.consultation_fee,
        "additional_charges": invoice.additional_charges,
        "total_amount": invoice.total_amount,
        "paid_amount": invoice.paid_amount,
        "balance": invoice.total_amount - invoice.paid_amount,
        "payment_status": invoice.payment_status,
        "payment_method": invoice.payment_method,
        "notes": invoice.notes,
        "created_at": str(invoice.created_at)
    }


@router.put("/{invoice_id}/payment")
def update_payment(
    invoice_id: str,
    data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == current_user.tenant_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.paid_amount = data.paid_amount
    if data.payment_method:
        invoice.payment_method = data.payment_method
    if data.notes:
        invoice.notes = data.notes

    if data.paid_amount >= invoice.total_amount:
        invoice.payment_status = "paid"
    elif data.paid_amount > 0:
        invoice.payment_status = "partial"
    else:
        invoice.payment_status = "unpaid"

    if data.payment_status:
        invoice.payment_status = data.payment_status

    db.commit()
    return {
        "message": "Payment updated",
        "payment_status": invoice.payment_status,
        "balance": invoice.total_amount - invoice.paid_amount
    }


@router.post("/{invoice_id}/charges")
def add_charge(
    invoice_id: str,
    data: AddCharge,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == current_user.tenant_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    charges = list(invoice.additional_charges or [])
    charges.append({"description": data.description, "amount": data.amount})

    from sqlalchemy.orm.attributes import flag_modified
    invoice.additional_charges = charges
    flag_modified(invoice, "additional_charges")

    invoice.total_amount = invoice.consultation_fee + sum(
        c.get("amount", 0) for c in charges
    )

    db.commit()
    return {
        "message": "Charge added",
        "total_amount": invoice.total_amount
    }


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == current_user.tenant_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.is_active = False
    db.commit()
    return {"message": "Invoice deleted"}
