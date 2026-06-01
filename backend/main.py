import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import all models so create_all sees them
import app.models  # noqa — registers all models with Base.metadata for create_all

from app.routers import auth, chat, dashboard, doctors, appointments, leads, superadmin, patients, visits, billing, branches, users, follow_ups, prescriptions, notes, voice, analytics, whatsapp, booking, notifications, doctor_portal, services, rooms, treatment_courses
from app.routers import settings as settings_router
from app.services.scheduler import start_scheduler, stop_scheduler


def _add_missing_columns():
    """Safely add new columns to existing tables (idempotent)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS "
            "reminder_sent BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "doctor_id UUID REFERENCES doctors(id)"
        ))
        conn.execute(text(
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS "
            "checked_in BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        conn.execute(text(
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS "
            "checked_in_at TIMESTAMP WITH TIME ZONE"
        ))
        conn.execute(text(
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS "
            "is_ready BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS services (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                name VARCHAR(255) NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                price NUMERIC(10,2),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rooms (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                name VARCHAR(100) NOT NULL,
                is_occupied BOOLEAN NOT NULL DEFAULT FALSE,
                current_appointment_id UUID,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        conn.execute(text(
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS "
            "room_id UUID REFERENCES rooms(id)"
        ))
        conn.execute(text(
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS "
            "service_name VARCHAR(255)"
        ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS treatment_courses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                patient_id UUID NOT NULL REFERENCES patients(id),
                patient_phone VARCHAR(50),
                service_name VARCHAR(255) NOT NULL,
                total_sessions INTEGER NOT NULL,
                completed_sessions INTEGER NOT NULL DEFAULT 0,
                price_per_course NUMERIC(10,2),
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )
        """))
        conn.commit()


def create_tables_with_retry(retries: int = 5, delay: int = 5):
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables ready")
            return
        except Exception as e:
            print(f"⚠️  DB attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("❌ Could not connect to database after all retries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables_with_retry()
    _add_missing_columns()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Clinic Chatbot API",
    description="Multi-tenant AI chatbot platform for clinics",
    version="1.0.0",
    lifespan=lifespan      # ← key change
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Block requests larger than 1MB — prevents memory exhaustion attacks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1_048_576:  # 1MB
            return StarletteResponse("Request too large", status_code=413)
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(leads.router)
app.include_router(superadmin.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(billing.router)
app.include_router(branches.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(follow_ups.router)
app.include_router(prescriptions.router)
app.include_router(notes.router)
app.include_router(voice.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)
app.include_router(whatsapp.router)
app.include_router(booking.router)
app.include_router(notifications.router)
app.include_router(doctor_portal.router)
app.include_router(services.router)
app.include_router(rooms.router)
app.include_router(treatment_courses.router)


@app.get("/")
def root():
    return {"message": "Clinic Chatbot API is running", "version": "1.0.0", "docs": "/docs"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}