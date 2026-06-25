"""Subscription business logic — the safe core, independent of any gateway.

Access is always DERIVED here from status + dates; the gateway only reports
events. A clinic gets access while trialing (within the trial window), while
active (within the paid period), or after cancelling until the period ends.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.services.plans import PLANS, TRIAL_DAYS, is_valid_plan


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_or_create_subscription(db, tenant: Tenant) -> Subscription:
    """Every clinic has exactly one subscription. New/legacy clinics get a
    fresh 3-day trial on first access."""
    sub = db.query(Subscription).filter(Subscription.tenant_id == tenant.id).first()
    if sub:
        return sub
    sub = Subscription(
        tenant_id=tenant.id,
        plan=tenant.plan or "starter",
        status="trialing",
        trial_ends_at=_now() + timedelta(days=TRIAL_DAYS),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def has_access(sub: Subscription) -> bool:
    """Is the clinic currently entitled to the paid product?"""
    now = _now()
    if sub.status == "active":
        end = _aware(sub.current_period_end)
        return end is None or end > now
    if sub.status == "trialing":
        end = _aware(sub.trial_ends_at)
        return end is not None and end > now
    if sub.status in ("cancelled", "past_due"):
        # Grace until the period they already paid for runs out.
        end = _aware(sub.current_period_end)
        return end is not None and end > now
    return False  # expired


def effective_status(sub: Subscription) -> str:
    """Normalize the stored status against the clock (a trial whose date has
    passed reads as 'expired')."""
    if sub.status == "trialing" and not has_access(sub):
        return "expired"
    if sub.status in ("active", "cancelled", "past_due") and not has_access(sub):
        return "expired"
    return sub.status


def status_payload(sub: Subscription) -> dict:
    now = _now()
    eff = effective_status(sub)
    trial_end = _aware(sub.trial_ends_at)
    period_end = _aware(sub.current_period_end)
    days_left = None
    ref_end = trial_end if eff == "trialing" else period_end
    if ref_end:
        days_left = max(0, (ref_end - now).days)
    plan = PLANS.get(sub.plan, PLANS["starter"])
    return {
        "plan": sub.plan,
        "plan_label": plan["label"],
        "price": plan["price"],
        "status": eff,
        "has_access": has_access(sub),
        "is_trial": eff == "trialing",
        "cancel_at_period_end": sub.cancel_at_period_end,
        "trial_ends_at": str(trial_end) if trial_end else None,
        "current_period_end": str(period_end) if period_end else None,
        "days_left": days_left,
        "gateway": sub.gateway,
    }


def begin_checkout(db, sub: Subscription, plan_key: str, ref: str, gateway: str) -> None:
    """Record an in-flight checkout so its webhook can be matched back."""
    sub.checkout_ref = ref
    sub.pending_plan = plan_key
    sub.gateway = gateway
    db.commit()


def activate(db, sub: Subscription, plan_key: str, *, gateway: str,
             subscription_id: str | None = None, customer_id: str | None = None,
             period_days: int = 30) -> None:
    """Mark a clinic as paid/active for one billing period and sync tenant.plan."""
    if not is_valid_plan(plan_key):
        plan_key = "starter"
    sub.plan = plan_key
    sub.status = "active"
    sub.gateway = gateway
    sub.cancel_at_period_end = False
    sub.current_period_end = _now() + timedelta(days=period_days)
    sub.pending_plan = None
    sub.checkout_ref = None
    if subscription_id:
        sub.gateway_subscription_id = subscription_id
    if customer_id:
        sub.gateway_customer_id = customer_id
    tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
    if tenant:
        tenant.plan = plan_key
    db.commit()


def cancel(db, sub: Subscription, *, immediate: bool = False) -> None:
    """Cancel anytime. Default: keep access until the current period ends."""
    sub.cancel_at_period_end = True
    if immediate or not _aware(sub.current_period_end):
        sub.status = "expired"
        sub.current_period_end = _now()
    else:
        sub.status = "cancelled"
    db.commit()


def apply_webhook_event(db, event: dict) -> bool:
    """Update the matching subscription from a verified gateway event."""
    ref = event.get("checkout_ref")
    if not ref:
        return False
    sub = db.query(Subscription).filter(Subscription.checkout_ref == ref).first()
    if not sub:
        sub = db.query(Subscription).filter(
            Subscription.gateway_subscription_id == event.get("subscription_id")
        ).first()
    if not sub:
        return False
    etype = event.get("type")
    if etype == "paid":
        activate(db, sub, sub.pending_plan or sub.plan, gateway=sub.gateway or "safepay",
                 subscription_id=event.get("subscription_id"),
                 customer_id=event.get("customer_id"))
    elif etype == "cancelled":
        cancel(db, sub)
    elif etype == "failed":
        sub.status = "past_due"
        db.commit()
    return True


def expire_due_subscriptions(db) -> int:
    """Scheduler: flip trials/periods that have ended to 'expired'."""
    now = _now()
    count = 0
    subs = db.query(Subscription).filter(
        Subscription.status.in_(["trialing", "active", "cancelled", "past_due"])
    ).all()
    for sub in subs:
        if not has_access(sub) and sub.status != "expired":
            sub.status = "expired"
            count += 1
    if count:
        db.commit()
    return count
