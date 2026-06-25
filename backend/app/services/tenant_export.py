# Build a complete, portable export of ONE clinic's data.
#
# Every business table is tenant-scoped (tenant_id), so a clinic's data is just
# the rows where tenant_id == theirs. We dump each table to a CSV and bundle the
# CSVs into a single ZIP the clinic can download and open in Excel.
#
# Use cases: data portability ("give me my data"), a clinic leaving with their
# records, and a human-readable companion to the disaster-recovery DB backups.
import csv
import io
import zipfile
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.visit import VisitRecord
from app.models.invoice import Invoice
from app.models.chat import ChatSession, Lead
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.follow_up import FollowUp
from app.models.prescription import Prescription
from app.models.note import Note
from app.models.treatment_session import TreatmentSession
from app.models.knowledge import KnowledgeEntry

# (filename, model). Order is just for readability of the ZIP.
_TABLES = [
    ("patients.csv", Patient),
    ("appointments.csv", Appointment),
    ("visits.csv", VisitRecord),
    ("invoices.csv", Invoice),
    ("leads.csv", Lead),
    ("chat_sessions.csv", ChatSession),
    ("doctors.csv", Doctor),
    ("services.csv", Service),
    ("follow_ups.csv", FollowUp),
    ("prescriptions.csv", Prescription),
    ("notes.csv", Note),
    ("treatment_sessions.csv", TreatmentSession),
    ("knowledge_base.csv", KnowledgeEntry),
]

# Columns left out of the export:
#   - secrets/tokens (never leave the system)
#   - tenant_id: an internal identifier, identical on every row, meaningless to
#     the clinic. Dropped as noise. (Row `id` and foreign keys like patient_id
#     are kept so records stay linkable / re-importable.)
_SKIP_COLUMNS = {"session_token", "hashed_password", "tenant_id"}


def _rows_to_csv(model, rows) -> str:
    columns = [c.name for c in model.__table__.columns if c.name not in _SKIP_COLUMNS]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([_cell(getattr(r, c)) for c in columns])
    return buf.getvalue()


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, default=str, ensure_ascii=False)
    return str(value)


def build_tenant_export_zip(db: Session, tenant_id) -> tuple[bytes, dict]:
    """Return (zip_bytes, counts) for all of one tenant's data."""
    counts: dict[str, int] = {}
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, model in _TABLES:
            rows = db.query(model).filter(model.tenant_id == tenant_id).all()
            counts[filename] = len(rows)
            zf.writestr(filename, _rows_to_csv(model, rows))
        # A small manifest so the recipient knows what/when.
        manifest = [
            "ClinicBot data export",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Tenant: {tenant_id}",
            "",
            "Row counts:",
        ] + [f"  {name}: {n}" for name, n in counts.items()]
        zf.writestr("README.txt", "\n".join(manifest) + "\n")
    return mem.getvalue(), counts
