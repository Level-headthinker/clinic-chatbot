"""
Demo seed script for Clinipilot.
Run: python seed_demo.py
Creates a demo clinic with doctors, patients, appointments, invoices, services, rooms.
Safe to run multiple times — skips if demo tenant already exists.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone, timedelta, date
from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.branch import Branch
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.visit import VisitRecord
from app.models.invoice import Invoice
from app.models.service import Service
from app.models.room import Room
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

def h(pw): return pwd_context.hash(pw)
def now(): return datetime.now(timezone.utc)
def today(): return now().replace(hour=0, minute=0, second=0, microsecond=0)
def slot(h, m=0, offset_days=0): return today() + timedelta(days=offset_days, hours=h, minutes=m)

try:
    # ── Check if demo already exists ─────────────────────────────────────────
    existing = db.query(Tenant).filter(Tenant.slug == "demo-clinic").first()
    if existing:
        print("Demo data already exists. Skipping.")
        sys.exit(0)

    print("Seeding demo data...")

    # ── Tenant ────────────────────────────────────────────────────────────────
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Noor Skin & Wellness Clinic",
        slug="demo-clinic",
        plan="growth",
        bot_name="Noor Assistant",
        welcome_message="Assalam o Alaikum! Welcome to Noor Skin & Wellness Clinic. How can I help you today?",
        primary_color="#0d9488",
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    # ── Branch ────────────────────────────────────────────────────────────────
    branch = Branch(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Main Branch - Gulberg",
        slug="gulberg",
        address="23-B, MM Alam Road, Gulberg III",
        city="Lahore",
        phone="0300-1234567",
        working_hours="Mon-Sat: 10:00 AM - 8:00 PM",
        is_active=True,
    )
    db.add(branch)
    db.flush()

    # ── Admin user ────────────────────────────────────────────────────────────
    admin = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        full_name="Admin",
        email="admin@demo-clinic.com",
        hashed_password=h("Demo1234"),
        role="admin",
        is_active=True,
    )
    db.add(admin)

    # ── Doctors ───────────────────────────────────────────────────────────────
    dr_ayesha = Doctor(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        name="Ayesha Malik",
        specialty="Dermatologist",
        qualification="MBBS, DDVL (London)",
        bio="Dr. Ayesha has 8 years of experience in medical and cosmetic dermatology. She specializes in skin rejuvenation and laser treatments.",
        fee="3000 PKR",
        treatments=["Hydra Facial", "Laser Hair Removal", "Chemical Peel", "Botox", "Skin Whitening"],
        timings=[
            {"day": "Monday", "from": "10:00 AM", "to": "05:00 PM"},
            {"day": "Tuesday", "from": "10:00 AM", "to": "05:00 PM"},
            {"day": "Wednesday", "from": "10:00 AM", "to": "05:00 PM"},
            {"day": "Thursday", "from": "10:00 AM", "to": "05:00 PM"},
            {"day": "Saturday", "from": "10:00 AM", "to": "02:00 PM"},
        ],
        is_ready=False,
        is_active=True,
    )

    dr_hassan = Doctor(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        name="Hassan Raza",
        specialty="Cosmetologist",
        qualification="MBBS, Diploma Cosmetology",
        bio="Dr. Hassan specializes in non-surgical cosmetic procedures and hair restoration treatments with over 5 years of clinical experience.",
        fee="2500 PKR",
        treatments=["Hydra Facial", "Hair PRP", "Mesotherapy", "Microneedling", "Cleanup"],
        timings=[
            {"day": "Monday", "from": "02:00 PM", "to": "08:00 PM"},
            {"day": "Wednesday", "from": "02:00 PM", "to": "08:00 PM"},
            {"day": "Friday", "from": "02:00 PM", "to": "08:00 PM"},
            {"day": "Saturday", "from": "02:00 PM", "to": "07:00 PM"},
        ],
        is_ready=True,
        is_active=True,
    )

    dr_sana = Doctor(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        name="Sana Tariq",
        specialty="Aesthetic Physician",
        qualification="MBBS, Fellowship Aesthetic Medicine",
        bio="Dr. Sana is known for natural-looking aesthetic results. She focuses on lip fillers, face contouring, and anti-aging treatments.",
        fee="3500 PKR",
        treatments=["Botox", "Lip Filler", "Face Contouring", "Anti-Aging Treatment", "Chemical Peel"],
        timings=[
            {"day": "Tuesday", "from": "12:00 PM", "to": "07:00 PM"},
            {"day": "Thursday", "from": "12:00 PM", "to": "07:00 PM"},
            {"day": "Saturday", "from": "10:00 AM", "to": "04:00 PM"},
        ],
        is_ready=False,
        is_active=True,
    )

    db.add_all([dr_ayesha, dr_hassan, dr_sana])
    db.flush()

    # ── Doctor logins ─────────────────────────────────────────────────────────
    user_ayesha = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        doctor_id=dr_ayesha.id,
        full_name="Dr. Ayesha",
        email="ayesha@demo-clinic.com",
        hashed_password=h("Doctor1234"),
        role="doctor",
        is_active=True,
    )
    user_hassan = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        branch_id=branch.id,
        doctor_id=dr_hassan.id,
        full_name="Dr. Hassan",
        email="hassan@demo-clinic.com",
        hashed_password=h("Doctor1234"),
        role="doctor",
        is_active=True,
    )
    db.add_all([user_ayesha, user_hassan])

    # ── Services ──────────────────────────────────────────────────────────────
    services_data = [
        ("Hydra Facial", 60, 5000),
        ("Laser Hair Removal", 45, 8000),
        ("Chemical Peel", 30, 4000),
        ("Botox", 30, 15000),
        ("Hair PRP", 60, 12000),
        ("Mesotherapy", 45, 7000),
        ("Microneedling", 45, 6000),
        ("Lip Filler", 30, 18000),
        ("Cleanup", 30, 2500),
        ("Skin Whitening", 60, 6000),
    ]
    services = []
    for name, duration, price in services_data:
        s = Service(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            branch_id=branch.id,
            name=name,
            duration_minutes=duration,
            price=price,
            is_active=True,
        )
        db.add(s)
        services.append(s)

    # ── Rooms ─────────────────────────────────────────────────────────────────
    room1 = Room(id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id, name="Treatment Room 1", is_occupied=False, is_active=True)
    room2 = Room(id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id, name="Treatment Room 2", is_occupied=True, is_active=True)
    room3 = Room(id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id, name="Laser Room", is_occupied=False, is_active=True)
    room4 = Room(id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id, name="Consultation Room", is_occupied=False, is_active=True)
    db.add_all([room1, room2, room3, room4])
    db.flush()

    # ── Patients ──────────────────────────────────────────────────────────────
    patients_data = [
        ("Fatima Zahra", "0300-1111111", 26, "Female", "B+", None, None),
        ("Ali Hassan", "0301-2222222", 34, "Male", "O+", None, "Hypertension"),
        ("Maryam Iqbal", "0302-3333333", 22, "Female", "A+", None, None),
        ("Usman Khan", "0303-4444444", 45, "Male", "AB+", "Penicillin", "Diabetes"),
        ("Zainab Ahmed", "0304-5555555", 30, "Female", "O-", None, None),
        ("Hamza Ali", "0305-6666666", 28, "Male", "B+", None, None),
        ("Sara Malik", "0306-7777777", 35, "Female", "A-", None, "Thyroid"),
        ("Bilal Chaudhry", "0307-8888888", 40, "Male", "O+", None, None),
        ("Nadia Hussain", "0308-9999999", 25, "Female", "B-", None, None),
        ("Tariq Mehmood", "0309-0000000", 52, "Male", "A+", "Aspirin", "Blood Pressure"),
    ]

    patients = []
    for name, phone, age, gender, blood, allergies, conditions in patients_data:
        p = Patient(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            primary_branch_id=branch.id,
            name=name,
            phone=phone,
            age=age,
            gender=gender,
            blood_group=blood,
            allergies=allergies,
            chronic_conditions=conditions,
            is_active=True,
        )
        db.add(p)
        patients.append(p)
    db.flush()

    # ── Today's appointments ──────────────────────────────────────────────────
    # Expected (not checked in)
    appt1 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_ayesha.id, patient_name="Fatima Zahra", patient_phone="0300-1111111",
        patient_concern="Hydra Facial session", service_name="Hydra Facial",
        slot_datetime=slot(14, 0), status="confirmed", checked_in=False, is_active=True,
    )
    appt2 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_hassan.id, patient_name="Hamza Ali", patient_phone="0305-6666666",
        patient_concern="Hair PRP treatment", service_name="Hair PRP",
        slot_datetime=slot(15, 0), status="pending", checked_in=False, is_active=True,
    )
    appt3 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_sana.id, patient_name="Sara Malik", patient_phone="0306-7777777",
        patient_concern="Lip filler consultation", service_name="Lip Filler",
        slot_datetime=slot(16, 0), status="confirmed", checked_in=False, is_active=True,
    )

    # Waiting queue (checked in)
    appt4 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_ayesha.id, patient_name="Maryam Iqbal", patient_phone="0302-3333333",
        patient_concern="Skin whitening treatment", service_name="Skin Whitening",
        slot_datetime=slot(11, 0), status="confirmed",
        checked_in=True, checked_in_at=now() - timedelta(minutes=25),
        is_active=True,
    )
    appt5 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_hassan.id, patient_name="Nadia Hussain", patient_phone="0308-9999999",
        patient_concern="Cleanup facial", service_name="Cleanup",
        slot_datetime=slot(12, 0), status="pending",
        checked_in=True, checked_in_at=now() - timedelta(minutes=10),
        is_active=True,
    )

    # With doctor (in progress)
    appt6 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_ayesha.id, patient_name="Zainab Ahmed", patient_phone="0304-5555555",
        patient_concern="Chemical peel session", service_name="Chemical Peel",
        slot_datetime=slot(10, 0), status="in_progress",
        checked_in=True, checked_in_at=now() - timedelta(minutes=45),
        room_id=room2.id, is_active=True,
    )

    # Completed today
    appt7 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_hassan.id, patient_name="Ali Hassan", patient_phone="0301-2222222",
        patient_concern="Mesotherapy", service_name="Mesotherapy",
        slot_datetime=slot(9, 0), status="completed",
        checked_in=True, checked_in_at=now() - timedelta(hours=3),
        is_active=True,
    )
    appt8 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_sana.id, patient_name="Usman Khan", patient_phone="0303-4444444",
        patient_concern="Botox treatment", service_name="Botox",
        slot_datetime=slot(10, 30), status="completed",
        checked_in=True, checked_in_at=now() - timedelta(hours=2),
        is_active=True,
    )
    appt9 = Appointment(
        id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
        doctor_id=dr_ayesha.id, patient_name="Bilal Chaudhry", patient_phone="0307-8888888",
        patient_concern="Laser hair removal - legs", service_name="Laser Hair Removal",
        slot_datetime=slot(11, 30), status="no_show", checked_in=False, is_active=True,
    )

    db.add_all([appt1, appt2, appt3, appt4, appt5, appt6, appt7, appt8, appt9])

    # ── Past appointments (last 30 days) ──────────────────────────────────────
    past_appts = []
    past_data = [
        (dr_ayesha.id, "Fatima Zahra", "0300-1111111", "Hydra Facial", -3, "completed"),
        (dr_hassan.id, "Ali Hassan", "0301-2222222", "Hair PRP", -3, "completed"),
        (dr_sana.id, "Maryam Iqbal", "0302-3333333", "Botox", -5, "completed"),
        (dr_ayesha.id, "Usman Khan", "0303-4444444", "Chemical Peel", -5, "completed"),
        (dr_hassan.id, "Zainab Ahmed", "0304-5555555", "Mesotherapy", -7, "completed"),
        (dr_ayesha.id, "Hamza Ali", "0305-6666666", "Skin Whitening", -7, "completed"),
        (dr_sana.id, "Sara Malik", "0306-7777777", "Lip Filler", -10, "completed"),
        (dr_hassan.id, "Bilal Chaudhry", "0307-8888888", "Microneedling", -10, "completed"),
        (dr_ayesha.id, "Nadia Hussain", "0308-9999999", "Hydra Facial", -12, "completed"),
        (dr_sana.id, "Tariq Mehmood", "0309-0000000", "Botox", -12, "cancelled"),
        (dr_ayesha.id, "Fatima Zahra", "0300-1111111", "Laser Hair Removal", -14, "completed"),
        (dr_hassan.id, "Ali Hassan", "0301-2222222", "Hair PRP", -14, "completed"),
        (dr_ayesha.id, "Maryam Iqbal", "0302-3333333", "Skin Whitening", -17, "completed"),
        (dr_sana.id, "Usman Khan", "0303-4444444", "Face Contouring", -17, "completed"),
        (dr_hassan.id, "Zainab Ahmed", "0304-5555555", "Cleanup", -20, "completed"),
        (dr_ayesha.id, "Hamza Ali", "0305-6666666", "Hydra Facial", -20, "no_show"),
        (dr_sana.id, "Sara Malik", "0306-7777777", "Botox", -22, "completed"),
        (dr_hassan.id, "Bilal Chaudhry", "0307-8888888", "Mesotherapy", -22, "completed"),
        (dr_ayesha.id, "Nadia Hussain", "0308-9999999", "Chemical Peel", -25, "completed"),
        (dr_ayesha.id, "Tariq Mehmood", "0309-0000000", "Laser Hair Removal", -25, "completed"),
    ]

    for doc_id, pname, pphone, concern, day_offset, status in past_data:
        a = Appointment(
            id=uuid.uuid4(), tenant_id=tenant.id, branch_id=branch.id,
            doctor_id=doc_id, patient_name=pname, patient_phone=pphone,
            patient_concern=concern, service_name=concern,
            slot_datetime=slot(10, 0, offset_days=day_offset),
            status=status,
            checked_in=status in ("completed", "in_progress"),
            checked_in_at=slot(10, 0, offset_days=day_offset) if status == "completed" else None,
            reminder_sent=True,
            is_active=True,
        )
        past_appts.append(a)

    db.add_all(past_appts)

    # ── Visit records ─────────────────────────────────────────────────────────
    visit_data = [
        (patients[0], dr_ayesha, "Hydra Facial session", "Dehydrated skin, recommended 4-session course", 5000, -3),
        (patients[1], dr_hassan, "Hair thinning, requesting PRP", "Androgenetic alopecia grade 3", 12000, -3),
        (patients[2], dr_sana, "Fine lines around eyes", "Early periorbital aging, Botox administered", 15000, -5),
        (patients[3], dr_ayesha, "Uneven skin tone", "Post-inflammatory hyperpigmentation", 4000, -5),
        (patients[4], dr_hassan, "Dull skin, fatigue", "Vitamin deficiency, mesotherapy recommended", 7000, -7),
        (patients[5], dr_ayesha, "Dark spots on face", "Melasma, course of 6 peels recommended", 6000, -7),
        (patients[6], dr_sana, "Thin lips, wants fuller look", "Lip augmentation with 1ml HA filler", 18000, -10),
        (patients[7], dr_hassan, "Acne scars", "Atrophic scars, microneedling course started", 6000, -10),
        (patients[8], dr_ayesha, "Dry flaky skin", "Xerosis, hydra facial done", 5000, -12),
        (patients[0], dr_ayesha, "Follow-up hydra facial", "Good response, skin hydration improved", 5000, -14),
    ]

    visits = []
    for patient, doctor, complaint, diagnosis, fee, day_offset in visit_data:
        v = VisitRecord(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            branch_id=branch.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_date=slot(10, 0, offset_days=day_offset),
            complaint=complaint,
            diagnosis=diagnosis,
            fee=fee,
            is_active=True,
        )
        db.add(v)
        visits.append(v)
    db.flush()

    # ── Invoices ──────────────────────────────────────────────────────────────
    invoice_data = [
        (patients[0], visits[0], "INV-001", 5000, 5000, "paid", "cash"),
        (patients[1], visits[1], "INV-002", 12000, 12000, "paid", "card"),
        (patients[2], visits[2], "INV-003", 15000, 15000, "paid", "bank_transfer"),
        (patients[3], visits[3], "INV-004", 4000, 4000, "paid", "cash"),
        (patients[4], visits[4], "INV-005", 7000, 0, "unpaid", None),
        (patients[5], visits[5], "INV-006", 6000, 6000, "paid", "cash"),
        (patients[6], visits[6], "INV-007", 18000, 10000, "partial", "card"),
        (patients[7], visits[7], "INV-008", 6000, 6000, "paid", "cash"),
        (patients[8], visits[8], "INV-009", 5000, 5000, "paid", "cash"),
        (patients[0], visits[9], "INV-010", 5000, 5000, "paid", "cash"),
    ]

    for patient, visit, inv_num, total, paid, status, method in invoice_data:
        inv = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            branch_id=branch.id,
            patient_id=patient.id,
            visit_id=visit.id,
            invoice_number=inv_num,
            consultation_fee=total,
            total_amount=total,
            paid_amount=paid,
            payment_status=status,
            payment_method=method,
            is_active=True,
        )
        db.add(inv)

    db.commit()

    print("\nDemo data seeded successfully!")
    print("\nLogin credentials:")
    print("   Admin   -> admin@demo-clinic.com  / Demo1234")
    print("   Doctor  -> ayesha@demo-clinic.com / Doctor1234")
    print("   Doctor  -> hassan@demo-clinic.com / Doctor1234")
    print("\nClinic: Noor Skin & Wellness Clinic")
    print("Seeded:")
    print("   - 3 doctors")
    print("   - 10 patients")
    print("   - 9 today's appointments (expected + waiting + in-progress + done)")
    print("   - 20 past appointments")
    print("   - 10 visit records")
    print("   - 10 invoices")
    print("   - 10 services")
    print("   - 4 rooms")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    raise
finally:
    db.close()
