"""
Backdated analytics seed — gives the Reports page something to analyze.

The base demo (seed_demo.py) creates appointments/invoices with created_at = now,
so every row lands in "today" and the weekly/monthly/yearly reports look flat.
This script layers in extra appointments, invoices, leads and chat sessions whose
created_at is spread across the last ~120 days, plus a WhatsApp usage row — so the
Daily / Weekly / Monthly / Yearly views and the new-vs-returning split all differ.

Run AFTER seed_demo.py:
    python seed_reports_demo.py

Idempotent: re-running skips (keyed on the demo WhatsApp mapping).
Reuses the existing "demo-clinic" tenant/branch/doctors/patients.
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.chat import ChatSession, Lead
from app.models.doctor import Doctor
from app.models.invoice import Invoice
from app.models.patient import Patient
from app.models.tenant import Tenant
from app.models.whatsapp_number import WhatsAppNumberMapping

MARKER_PNID = "DEMO_ANALYTICS_PNID"   # idempotency key
random.seed(42)                        # reproducible spread

db = SessionLocal()


def now_utc():
    return datetime.now(timezone.utc)


# Working-hour pool; 14:00 deliberately over-weighted so a "busiest slot" emerges.
HOURS = [10, 11, 12, 13, 14, 14, 14, 15, 16, 17, 18]
CONCERNS = [
    "Hydra Facial", "Laser Hair Removal", "Chemical Peel", "Botox",
    "Hair PRP", "Mesotherapy", "Microneedling", "Lip Filler", "Skin Whitening",
]
LEAD_CONCERNS = [
    "Acne treatment enquiry", "Laser hair removal pricing", "Botox consultation",
    "Skin whitening package", "Hair fall treatment", "Wants appointment soon",
]
CHAT_SNIPPETS = [
    "Assalam o Alaikum, I want to book an appointment",
    "What is the fee for hydra facial?",
    "Do you have laser hair removal?",
    "mujhe skin specialist se milna hai",
    "What are your timings?",
    "Botox ki price kya hai?",
    "Can I come tomorrow?",
    "Hair PRP ke baare mein batayein",
]

try:
    tenant = db.query(Tenant).filter(Tenant.slug == "demo-clinic").first()
    if not tenant:
        print("Demo clinic not found. Run  python seed_demo.py  first.")
        sys.exit(1)

    if db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.phone_number_id == MARKER_PNID
    ).first():
        print("Analytics demo already seeded. Skipping.")
        sys.exit(0)

    branch = db.query(Branch).filter(Branch.tenant_id == tenant.id).first()
    doctors = db.query(Doctor).filter(Doctor.tenant_id == tenant.id).all()
    patients = db.query(Patient).filter(Patient.tenant_id == tenant.id).all()
    if not (branch and doctors and patients):
        print("Demo clinic is missing branch/doctors/patients. Re-run seed_demo.py.")
        sys.exit(1)

    print("Seeding backdated analytics data across the last 120 days...")

    # Over-weight the first doctor so a clear "busiest doctor" emerges.
    doctor_pool = [doctors[0]] * 3 + doctors[1:]

    active_slots = set()   # guard the partial-unique index on pending/confirmed
    appts, invoices, leads, sessions = [], [], [], []
    inv_counter = 1

    # ── Appointments + invoices, spread across 120 days ───────────────────────
    for day_offset in range(1, 121):
        # 0–3 appointments per day, busier in the recent past
        n = random.choices([0, 1, 2, 3], weights=[3, 5, 4, 2])[0]
        day = now_utc() - timedelta(days=day_offset)
        for _ in range(n):
            doctor = random.choice(doctor_pool)
            patient = random.choice(patients)          # reuse → returning patients
            hour = random.choice(HOURS)
            slot_dt = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Past appointments: mostly completed, some no_show / cancelled.
            status = random.choices(
                ["completed", "completed", "completed", "no_show", "cancelled"],
                weights=[5, 5, 5, 2, 1],
            )[0]
            concern = random.choice(CONCERNS)
            appt = Appointment(
                tenant_id=tenant.id, branch_id=branch.id, doctor_id=doctor.id,
                patient_name=patient.name, patient_phone=patient.phone,
                patient_concern=concern, service_name=concern,
                slot_datetime=slot_dt, status=status,
                checked_in=status == "completed",
                checked_in_at=slot_dt if status == "completed" else None,
                reminder_sent=True, is_active=True,
                created_at=day,                          # ← backdated booking date
            )
            appts.append(appt)

            if status == "completed":
                amount = random.choice([3000, 4000, 5000, 6000, 7000, 12000, 15000, 18000])
                paid = amount if random.random() > 0.15 else int(amount * 0.5)
                invoices.append(Invoice(
                    tenant_id=tenant.id, branch_id=branch.id, patient_id=patient.id,
                    invoice_number=f"INV-D-{inv_counter:04d}",
                    consultation_fee=amount, total_amount=amount, paid_amount=paid,
                    payment_status="paid" if paid == amount else "partial",
                    payment_method=random.choice(["cash", "card", "bank_transfer"]),
                    is_active=True, created_at=day,
                ))
                inv_counter += 1

    # ── A handful of upcoming (pending/confirmed) appointments ────────────────
    for day_offset in range(1, 10):
        day = now_utc() + timedelta(days=day_offset)
        doctor = random.choice(doctor_pool)
        patient = random.choice(patients)
        hour = random.choice(HOURS)
        slot_dt = day.replace(hour=hour, minute=random.choice([0, 30]), second=0, microsecond=0)
        key = (doctor.id, slot_dt)
        if key in active_slots:
            continue
        active_slots.add(key)
        appts.append(Appointment(
            tenant_id=tenant.id, branch_id=branch.id, doctor_id=doctor.id,
            patient_name=patient.name, patient_phone=patient.phone,
            patient_concern=random.choice(CONCERNS), service_name=random.choice(CONCERNS),
            slot_datetime=slot_dt, status=random.choice(["pending", "confirmed"]),
            is_active=True, created_at=now_utc() - timedelta(days=random.randint(0, 3)),
        ))

    # ── Leads, spread across 90 days ──────────────────────────────────────────
    for i in range(35):
        day = now_utc() - timedelta(days=random.randint(0, 90))
        leads.append(Lead(
            tenant_id=tenant.id, branch_id=branch.id,
            name=f"Lead {i + 1}",
            phone=f"03{random.randint(10, 49)}{random.randint(1000000, 9999999)}",
            concern=random.choice(LEAD_CONCERNS),
            source=random.choice(["chatbot", "whatsapp", "self_booking"]),
            status=random.choice(["new", "new", "contacted", "converted"]),
            is_active=True, created_at=day,
        ))

    # ── Chat sessions with messages, spread across 90 days ────────────────────
    for i in range(45):
        day = now_utc() - timedelta(days=random.randint(0, 90))
        turns = random.randint(2, 5)
        msgs = []
        for t in range(turns):
            msgs.append({"role": "user", "content": random.choice(CHAT_SNIPPETS)})
            msgs.append({"role": "assistant", "content": "Sure, I can help with that."})
        sessions.append(ChatSession(
            tenant_id=tenant.id, branch_id=branch.id,
            session_token=f"seed:analytics:{i}",
            messages=msgs,
            language=random.choice(["en", "ur-roman"]),
            patient_name=f"Visitor {i + 1}",
            current_intent="book_appointment",
            is_active=True, created_at=day,
        ))

    # ── WhatsApp usage row (powers /whatsapp/usage + superadmin number page) ──
    reset = (now_utc().replace(day=1) + timedelta(days=32)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    mapping = WhatsAppNumberMapping(
        tenant_id=tenant.id, branch_id=branch.id,
        phone_number_id=MARKER_PNID, whatsapp_number="+923004445566",
        is_active=True, message_limit_monthly=1000,
        messages_used_this_month=347, limit_reset_date=reset,
    )

    db.add_all(appts)
    db.add_all(invoices)
    db.add_all(leads)
    db.add_all(sessions)
    db.add(mapping)
    db.commit()

    print("\nAnalytics demo seeded successfully!")
    print(f"   + {len(appts)} appointments (backdated over 120 days)")
    print(f"   + {len(invoices)} invoices (revenue)")
    print(f"   + {len(leads)} leads")
    print(f"   + {len(sessions)} chat sessions")
    print("   + 1 WhatsApp number with monthly usage (347 / 1000)")
    print("\nLog in as  admin@demo-clinic.com / Demo1234  ->  Reports")
    print("Try the period selector: Daily / Weekly / Monthly / Yearly.")

except SystemExit:
    raise
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    raise
finally:
    db.close()
