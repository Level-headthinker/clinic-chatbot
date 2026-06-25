"""Subscription plan definitions — single source of truth for pricing & trial.

Prices are in PKR/month. Kept here (not the DB) so they're versioned with code;
the tenant only stores which plan it's on. Mirrors frontend/src/config/plans.js.
"""

TRIAL_DAYS = 3
CURRENCY = "PKR"

PLANS = {
    "starter": {
        "key": "starter", "label": "Starter", "price": 3000, "color": "#6b7280",
        "tagline": "Everything to get your clinic on WhatsApp.",
        "highlights": [
            "AI WhatsApp + web chat bot",
            "Appointment booking & reminders",
            "Patients, leads & billing",
            "Knowledge base",
        ],
    },
    "growth": {
        "key": "growth", "label": "Growth", "price": 8000, "color": "#2563eb",
        "tagline": "Scale across branches with full analytics.",
        "highlights": [
            "Everything in Starter",
            "Multiple branches",
            "Analytics & reports",
            "Team inbox",
        ],
    },
    "enterprise": {
        "key": "enterprise", "label": "Enterprise", "price": 20000, "color": "#7c3aed",
        "tagline": "Voice agent and unlimited scale.",
        "highlights": [
            "Everything in Growth",
            "AI voice agent (calls)",
            "Priority support",
            "Custom limits",
        ],
    },
}

PLAN_KEYS = list(PLANS.keys())


def plan_price(plan_key: str) -> int:
    return PLANS.get(plan_key, PLANS["starter"])["price"]


def is_valid_plan(plan_key: str) -> bool:
    return plan_key in PLANS


def public_plans() -> list[dict]:
    """Plans list for the frontend pricing page."""
    return [
        {
            "key": p["key"], "label": p["label"], "price": p["price"],
            "currency": CURRENCY, "color": p["color"],
            "tagline": p["tagline"], "highlights": p["highlights"],
        }
        for p in PLANS.values()
    ]
