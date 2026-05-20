from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import all models so create_all sees them
from app.models import (  # noqa: F401
    appointment, chat, doctor, invoice,
    patient, tenant, user, visit
)
from app.models.flagged_log import FlaggedLog  # noqa: F401 — Phase 4

from app.routers import (
    auth, chat, doctors, appointments,
    leads, superadmin, patients, visits, billing
)

app = FastAPI(
    title="Clinic Chatbot API",
    description="Multi-tenant AI chatbot platform for clinics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

import time

def create_tables_with_retry(retries: int = 5, delay: int = 3):
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables ready")
            return
        except Exception as e:
            print(f"⚠️ DB connection attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("❌ Could not connect to database after multiple attempts")

create_tables_with_retry()

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(leads.router)
app.include_router(superadmin.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(billing.router)


@app.get("/")
def root():
    return {
        "message": "Clinic Chatbot API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}