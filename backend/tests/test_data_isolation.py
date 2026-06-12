"""
Test: clinic data isolation + role scoping
Part 1 (always runs): privilege-escalation guards — a branch admin must not
manage users outside their branch or grant tenant-level admin.
Part 2 (needs TEST_DATABASE_URL): two clinics in a real Postgres, asserting
Clinic B's queries can never see Clinic A's rows.
"""
import os
import uuid

import pytest
from fastapi import HTTPException

from app.routers.users import _require_manage_scope, _require_role_grant_allowed


class _U:
    def __init__(self, branch_id=None):
        self.branch_id = branch_id


class TestRoleScoping:
    def test_branch_admin_cannot_touch_other_branch_user(self):
        with pytest.raises(HTTPException) as exc:
            _require_manage_scope(_U(branch_id="branch-A"), _U(branch_id="branch-B"))
        assert exc.value.status_code == 403

    def test_branch_admin_cannot_touch_tenant_level_user(self):
        # Tenant-level users have branch_id=None — e.g. the clinic owner.
        with pytest.raises(HTTPException):
            _require_manage_scope(_U(branch_id="branch-A"), _U(branch_id=None))

    def test_branch_admin_manages_own_branch(self):
        _require_manage_scope(_U(branch_id="branch-A"), _U(branch_id="branch-A"))

    def test_tenant_admin_manages_everyone(self):
        _require_manage_scope(_U(branch_id=None), _U(branch_id="branch-B"))

    def test_branch_admin_cannot_grant_admin_role(self):
        with pytest.raises(HTTPException) as exc:
            _require_role_grant_allowed(_U(branch_id="branch-A"), "admin")
        assert exc.value.status_code == 403

    def test_branch_admin_can_grant_staff_role(self):
        _require_role_grant_allowed(_U(branch_id="branch-A"), "staff")

    def test_tenant_admin_can_grant_admin_role(self):
        _require_role_grant_allowed(_U(branch_id=None), "admin")


# ── Full-DB isolation test (opt-in: needs a disposable Postgres) ──────────────

needs_db = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="set TEST_DATABASE_URL to a DISPOSABLE postgres database to run",
)


@needs_db
class TestDatabaseIsolation:
    @pytest.fixture()
    def db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base

        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_appointments_isolated(self, db):
        from app.models.appointment import Appointment
        from app.models.branch import Branch
        from app.models.doctor import Doctor
        from app.models.tenant import Tenant
        from datetime import datetime, timedelta

        def make_clinic(slug):
            t = Tenant(name=slug, slug=f"{slug}-{uuid.uuid4().hex[:6]}")
            db.add(t); db.flush()
            b = Branch(tenant_id=t.id, name=slug, slug=t.slug, is_main_branch=True)
            db.add(b); db.flush()
            d = Doctor(tenant_id=t.id, name=f"Doc {slug}", specialty="GP")
            db.add(d); db.flush()
            return t, b, d

        ta, ba, da = make_clinic("clinic-a")
        tb, bb, dbn = make_clinic("clinic-b")
        appt = Appointment(
            tenant_id=ta.id, branch_id=ba.id, doctor_id=da.id,
            patient_name="Secret Patient", patient_phone="03001112223",
            slot_datetime=datetime.now() + timedelta(days=1), status="pending",
        )
        db.add(appt); db.flush()

        rows_b = db.query(Appointment).filter(Appointment.tenant_id == tb.id).all()
        assert appt.id not in [r.id for r in rows_b], \
            "SECURITY FAILURE: Clinic B can see Clinic A's appointment"
        rows_a = db.query(Appointment).filter(Appointment.tenant_id == ta.id).all()
        assert appt.id in [r.id for r in rows_a]
