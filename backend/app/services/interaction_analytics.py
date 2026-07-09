"""The "learn" layer of the data feedback loop.

Turns the raw InteractionEvent rows into the few numbers that actually tell you
what to fix: conversion rate, what people ask about, and where the bot is weak
(KB misses, output-guard interventions). Per-tenant and always tenant-scoped.
"""
from datetime import datetime, timedelta

from sqlalchemy import func
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
