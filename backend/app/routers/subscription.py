"""Subscription & billing API.

  GET  /subscription            current status (auto-creates a 3-day trial)
  GET  /subscription/plans      public plan list (pricing)
  POST /subscription/checkout   start checkout for a plan → gateway URL (or test)
  POST /subscription/manual-confirm   simulate payment success (test mode only)
  POST /subscription/cancel     cancel anytime (keeps access until period end)
  POST /subscription/webhook    gateway → us (signature-verified; source of truth)

Security:
  • Only signature-verified webhooks (or the test-mode confirm with a secret)
    can mark a clinic 'active'. The frontend can never set paid status.
  • Every read/write is scoped to the caller's tenant.
  • Checkout/cancel require a clinic admin.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user, require_admin_user
from app.services.payments import get_provider, new_checkout_ref
from app.services.plans import is_valid_plan, public_plans
from app.services import subscription_service as subs

router = APIRouter(prefix="/subscription", tags=["Subscription"])


def _tenant(db: Session, user: User) -> Tenant:
    t = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return t


@router.get("/plans")
def list_plans():
    return {"plans": public_plans(), "trial_days": subs.TRIAL_DAYS, "currency": "PKR"}


@router.get("")
def my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = subs.get_or_create_subscription(db, _tenant(db, current_user))
    return subs.status_payload(sub)


class CheckoutIn(BaseModel):
    plan: str


@router.post("/checkout")
def checkout(
    data: CheckoutIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    if not is_valid_plan(data.plan):
        raise HTTPException(status_code=400, detail="Unknown plan")
    tenant = _tenant(db, current_user)
    sub = subs.get_or_create_subscription(db, tenant)

    provider = get_provider()
    ref = new_checkout_ref()
    subs.begin_checkout(db, sub, data.plan, ref, provider.name)

    base = settings.APP_BASE_URL.rstrip("/")
    try:
        result = provider.create_checkout(
            tenant_id=str(tenant.id),
            plan_key=data.plan,
            checkout_ref=ref,
            customer_email=current_user.email,
            success_url=f"{base}/subscription?status=success",
            cancel_url=f"{base}/subscription?status=cancelled",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not start checkout. Please try again.")
    return result


class ManualConfirmIn(BaseModel):
    ref: str


@router.post("/manual-confirm")
def manual_confirm(
    data: ManualConfirmIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Test-mode only: simulate a successful payment. Guarded by clinic-admin
    auth + the checkout_ref matching this tenant's pending checkout, and only
    works when PAYMENT_PROVIDER=manual (production uses the real gateway webhook)."""
    if settings.PAYMENT_PROVIDER != "manual":
        raise HTTPException(status_code=400, detail="Manual confirm is only available in test mode")
    tenant = _tenant(db, current_user)
    sub = subs.get_or_create_subscription(db, tenant)
    if not sub.checkout_ref or sub.checkout_ref != data.ref:
        raise HTTPException(status_code=400, detail="No matching pending checkout")
    subs.activate(db, sub, sub.pending_plan or sub.plan, gateway="manual")
    return subs.status_payload(sub)


@router.post("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    sub = subs.get_or_create_subscription(db, _tenant(db, current_user))
    subs.cancel(db, sub)   # keep access until the current period ends
    return subs.status_payload(sub)


@router.post("/webhook")
async def subscription_webhook(request: Request):
    """Gateway → us. The ONLY way a subscription becomes 'active'."""
    raw = await request.body()
    provider = get_provider()
    event = provider.verify_and_parse_webhook(raw, dict(request.headers))
    if event is None:
        return PlainTextResponse("ignored", status_code=200)  # bad sig / irrelevant
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        subs.apply_webhook_event(db, event)
    finally:
        db.close()
    return {"status": "ok"}
