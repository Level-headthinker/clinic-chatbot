"""
Demo WhatsApp conversations for the Conversations (Team Inbox) tab.

seed_reports_demo.py created web-style sessions (token 'seed:analytics:*'), so
the inbox showed only un-repliable web chats. This adds realistic *WhatsApp*
conversations (token 'wa:<number>') with varied, real-sounding bot replies —
a couple unread, one already in human-handling mode — so you can test take-over,
the reply box, and agent bubbles.

Run after seed_demo.py:  python seed_inbox_demo.py    (idempotent)
"""
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.branch import Branch
from app.models.chat import ChatSession
from app.models.tenant import Tenant

db = SessionLocal()


def ago(minutes):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


CONVERSATIONS = [
    {
        "phone": "923009990001", "name": "Ayesha Siddiqui", "lang": "en",
        "human": False, "unread": 2, "mins": 3,
        "messages": [
            ("user", "Hi, do you do hydra facial?"),
            ("assistant", "Yes! Dr. Ayesha Malik does Hydra Facial — the fee is 3000 PKR. Would you like to book an appointment?"),
            ("user", "What days is she available?"),
            ("assistant", "Dr. Ayesha is available Monday to Thursday 10am–5pm, and Saturday 10am–2pm. May I have your name to book?"),
            ("user", "Ayesha Siddiqui. Can I come this Saturday?"),
        ],
    },
    {
        "phone": "923009990002", "name": "Bilal Ahmed", "lang": "ur-roman",
        "human": False, "unread": 1, "mins": 12,
        "messages": [
            ("user", "Assalam o Alaikum, hair PRP ka rate kya hai?"),
            ("assistant", "Walaikum Assalam! Hair PRP Dr. Hassan Raza karte hain, fee 2500 PKR hai. Appointment book karein?"),
            ("user", "Haan, kal possible hai?"),
        ],
    },
    {
        "phone": "923009990003", "name": "Hina Tariq", "lang": "en",
        "human": True, "unread": 1, "mins": 6,
        "messages": [
            ("user", "I had a chemical peel last week and my skin is still red, is that normal?"),
            ("assistant", "I can only help with appointments and clinic information. Please discuss this directly with the doctor."),
            ("user", "Can someone from the clinic actually call me about this?"),
        ],
    },
    {
        "phone": "923009990004", "name": "Usman Sheikh", "lang": "en",
        "human": False, "unread": 0, "mins": 90,
        "messages": [
            ("user", "What are your timings today?"),
            ("assistant", "We're open Mon–Sat, 10:00 AM to 8:00 PM. Is there anything I can help you book?"),
            ("user", "No thanks, just checking."),
            ("assistant", "No problem — we're here whenever you need us. Take care!"),
        ],
    },
    {
        "phone": "923009990005", "name": "Mehwish Khan", "lang": "ur-roman",
        "human": False, "unread": 3, "mins": 1,
        "messages": [
            ("user", "Botox ki price kya hai?"),
            ("assistant", "Botox Dr. Sana Tariq karti hain, fee 3500 PKR hai. Aap ka naam bata dein to appointment book kar deti hoon."),
            ("user", "Mehwish Khan"),
            ("user", "Aur address kya hai aap ka?"),
            ("user", "Reply please"),
        ],
    },
]


try:
    tenant = db.query(Tenant).filter(Tenant.slug == "demo-clinic").first()
    if not tenant:
        print("Demo clinic not found. Run  python seed_demo.py  first.")
        sys.exit(1)
    branch = db.query(Branch).filter(Branch.tenant_id == tenant.id).first()

    marker = "wa:923009990001"
    if db.query(ChatSession).filter(ChatSession.session_token == marker).first():
        print("Inbox demo conversations already seeded. Skipping.")
        sys.exit(0)

    print("Seeding demo WhatsApp conversations for the inbox...")
    for c in CONVERSATIONS:
        msgs = [{"role": r, "content": t} for r, t in c["messages"]]
        db.add(ChatSession(
            tenant_id=tenant.id,
            branch_id=branch.id if branch else None,
            session_token=f"wa:{c['phone']}",
            messages=msgs,
            language=c["lang"],
            patient_name=c["name"],
            patient_phone="0" + c["phone"][2:],   # 923... -> 03...
            current_intent="book_appointment",
            human_handling=c["human"],
            unread_count=c["unread"],
            is_active=True,
            created_at=ago(c["mins"] + 30),
        ))
    db.commit()
    print(f"Seeded {len(CONVERSATIONS)} WhatsApp conversations.")
    print("Open the Conversations tab -> pick a WhatsApp chat -> Take over -> reply.")
    print("Note: actual delivery needs a live connected number; the inbox UI works regardless.")

except SystemExit:
    raise
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    raise
finally:
    db.close()
