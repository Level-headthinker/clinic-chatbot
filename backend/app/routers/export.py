# Per-clinic data export ("give me my data").
#   GET /export/my-data                 → the caller's own clinic (admin)
#   GET /export/clinic/{tenant_id}      → any clinic (superadmin only)
# Returns a ZIP of CSVs (one per table). The action is itself audit-logged.
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import io

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import require_admin_user, get_current_user
from app.services.tenant_export import build_tenant_export_zip
from app.services.audit import log_audit

router = APIRouter(prefix="/export", tags=["Export"])


def _zip_response(zip_bytes: bytes, tenant: Tenant) -> StreamingResponse:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = (tenant.slug if tenant else "clinic") or "clinic"
    filename = f"{slug}_export_{stamp}.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/my-data")
def export_my_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Download all of the calling admin's own clinic data as a ZIP of CSVs."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    zip_bytes, counts = build_tenant_export_zip(db, current_user.tenant_id)
    log_audit(
        db, tenant_id=current_user.tenant_id, action="export",
        entity_type="tenant", entity_id=current_user.tenant_id,
        summary=f"Exported clinic data ({sum(counts.values())} rows)",
        after=counts, user=current_user, request=request, commit=True,
    )
    return _zip_response(zip_bytes, tenant)


@router.get("/clinic/{tenant_id}")
def export_any_clinic(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Superadmin: export any clinic's data (e.g. on the clinic's request)."""
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin only")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    zip_bytes, counts = build_tenant_export_zip(db, tenant_id)
    log_audit(
        db, tenant_id=tenant_id, action="export",
        entity_type="tenant", entity_id=tenant_id,
        summary=f"Superadmin exported clinic data ({sum(counts.values())} rows)",
        after=counts, user=current_user, request=request, commit=True,
    )
    return _zip_response(zip_bytes, tenant)
