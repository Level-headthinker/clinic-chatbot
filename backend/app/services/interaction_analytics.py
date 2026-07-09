"""The "learn" layer of the data feedback loop.

Turns the raw InteractionEvent rows into the few numbers that actually tell you
what to fix: conversion rate, what people ask about, and where the bot is weak
(KB misses, output-guard interventions). Per-tenant and always tenant-scoped.
"""
from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.interaction_event import InteractionEvent


def summarize(db: Session, tenant_id, *, days: int = 30) -> dict:
    """Aggregate the last ``days`` of turns for one clinic.

    Returns a plain dict (JSON-ready) with the headline funnel + weak spots.
    """
    since = datetime.utcnow() - timedelta(days=days)
    base = db.query(InteractionEvent).filter(
        InteractionEvent.tenant_id == tenant_id,
        InteractionEvent.created_at >= since,
    )

    total = base.count()
    if not total:
        return {
            "days": days, "total_turns": 0, "booking_intent_turns": 0,
            "booked": 0, "leads_captured": 0, "conversion_rate": 0.0,
            "kb_miss_rate": 0.0, "output_flag_rate": 0.0,
            "intents": {}, "outcomes": {},
        }

    def _counts(column):
        rows = (
            db.query(column, func.count())
            .filter(
                InteractionEvent.tenant_id == tenant_id,
                InteractionEvent.created_at >= since,
            )
            .group_by(column)
            .all()
        )
        return {(k or "unknown"): n for k, n in rows}

    outcomes = _counts(InteractionEvent.outcome)
    intents = _counts(InteractionEvent.intent)

    booked = outcomes.get("booked", 0)
    leads = outcomes.get("lead_captured", 0)
    # Conversion is measured against turns where the patient WANTED to book —
    # counting it against every "what are your timings?" turn would be misleading.
    booking_intent_turns = intents.get("book_appointment", 0)
    conversion = round(booked / booking_intent_turns, 3) if booking_intent_turns else 0.0

    kb_misses = base.filter(InteractionEvent.kb_hit.is_(False)).count()
    flagged = base.filter(InteractionEvent.output_flagged.is_(True)).count()

    return {
        "days": days,
        "total_turns": total,
        "booking_intent_turns": booking_intent_turns,
        "booked": booked,
        "leads_captured": leads,
        # Of patients who tried to book, how many the bot actually booked.
        "conversion_rate": conversion,
        # How often the KB had NO answer — high = fill knowledge gaps.
        "kb_miss_rate": round(kb_misses / total, 3),
        # How often the output guard had to intervene — high = prompt/safety issue.
        "output_flag_rate": round(flagged / total, 3),
        "intents": dict(sorted(intents.items(), key=lambda kv: kv[1], reverse=True)),
        "outcomes": outcomes,
    }


def summarize_global(db: Session, *, days: int = 30) -> dict:
    """Superadmin-only: the feedback loop across ALL clinics.

    Returns platform totals plus a per-clinic rollup — including the safety
    (output-guard) rate, which is an internal ops signal we deliberately keep
    OUT of the per-clinic admin view. Use it to spot a misbehaving prompt or a
    clinic with a large knowledge gap. No PHI — all from InteractionEvent.
    """
    from app.models.tenant import Tenant

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            InteractionEvent.tenant_id,
            func.count().label("turns"),
            func.sum(case((InteractionEvent.outcome == "booked", 1), else_=0)).label("booked"),
            func.sum(case((InteractionEvent.intent == "book_appointment", 1), else_=0)).label("booking_intent"),
            func.sum(case((InteractionEvent.kb_hit.is_(False), 1), else_=0)).label("kb_misses"),
            func.sum(case((InteractionEvent.output_flagged.is_(True), 1), else_=0)).label("flagged"),
        )
        .filter(InteractionEvent.created_at >= since)
        .group_by(InteractionEvent.tenant_id)
        .all()
    )

    names = {t.id: t.name for t in db.query(Tenant.id, Tenant.name).all()}

    clinics = []
    tot_turns = tot_booked = tot_intent = tot_kb_miss = tot_flagged = 0
    for r in rows:
        tot_turns += r.turns
        tot_booked += r.booked or 0
        tot_intent += r.booking_intent or 0
        tot_kb_miss += r.kb_misses or 0
        tot_flagged += r.flagged or 0
        clinics.append({
            "tenant_id": str(r.tenant_id) if r.tenant_id else None,
            "clinic_name": names.get(r.tenant_id, "Unknown"),
            "turns": r.turns,
            "booked": r.booked or 0,
            "conversion_rate": round((r.booked or 0) / r.booking_intent, 3) if r.booking_intent else 0.0,
            "kb_miss_rate": round((r.kb_misses or 0) / r.turns, 3) if r.turns else 0.0,
            "output_flag_rate": round((r.flagged or 0) / r.turns, 3) if r.turns else 0.0,
        })

    # Worst offenders first — the clinics that need attention.
    clinics.sort(key=lambda c: (c["output_flag_rate"], c["kb_miss_rate"]), reverse=True)

    return {
        "days": days,
        "total_turns": tot_turns,
        "active_clinics": len(clinics),
        "booked": tot_booked,
        "conversion_rate": round(tot_booked / tot_intent, 3) if tot_intent else 0.0,
        "kb_miss_rate": round(tot_kb_miss / tot_turns, 3) if tot_turns else 0.0,
        "output_flag_rate": round(tot_flagged / tot_turns, 3) if tot_turns else 0.0,
        "clinics": clinics,
    }
