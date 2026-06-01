import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import all models so create_all sees them
import app.models  # noqa — registers all models with Base.metadata for create_all

from app.routers import auth, chat, dashboard, doctors, appointments, leads, superadmin, patients, visits, billing, branches, users, follow_ups, prescriptions, notes, voice, analytics, whatsapp, booking, notifications, doctor_portal, services, rooms, treatment_sessions
from app.routers import settings as settings_router
from app.services.scheduler import start_scheduler, stop_scheduler


def _run_sql(conn, sql: str, label: str = ""):
    """Run a single SQL statement, log failures but never crash startup."""
    from sqlalchemy import text
    try:
        conn.execute(text(sql))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️  Migration skipped [{label}]: {e}")


def _add_missing_columns():
    """Safely add new columns to existing tables — each statement is independent."""
    with engine.connect() as conn:
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN NOT NULL DEFAULT FALSE",
            "appointments.reminder_sent")
        _run_sql(conn,
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS doctor_id UUID REFERENCES doctors(id)",
            "users.doctor_id")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS checked_in BOOLEAN NOT NULL DEFAULT FALSE",
            "appointments.checked_in")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMP WITH TIME ZONE",
            "appointments.checked_in_at")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS is_ready BOOLEAN NOT NULL DEFAULT FALSE",
            "doctors.is_ready")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS services (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                name VARCHAR(255) NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                price NUMERIC(10,2),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now()
            )""", "create services")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS rooms (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                name VARCHAR(100) NOT NULL,
                is_occupied BOOLEAN NOT NULL DEFAULT FALSE,
                current_appointment_id UUID,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now()
            )""", "create rooms")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS room_id UUID REFERENCES rooms(id)",
            "appointments.room_id")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS service_name VARCHAR(255)",
            "appointments.service_name")
        _run_sql(conn, """
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'treatment_courses')
                   AND NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'treatment_sessions')
                THEN ALTER TABLE treatment_courses RENAME TO treatment_sessions;
                END IF;
            END $$""", "rename treatment_courses table")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS treatment_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                patient_id UUID NOT NULL REFERENCES patients(id),
                patient_phone VARCHAR(50),
                service_name VARCHAR(255) NOT NULL,
                total_sessions INTEGER NOT NULL,
                completed_sessions INTEGER NOT NULL DEFAULT 0,
                price_per_session NUMERIC(10,2),
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )""", "create treatment_sessions")
        _run_sql(conn, """
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.columns
                           WHERE table_name='treatment_sessions' AND column_name='price_per_course')
                THEN ALTER TABLE treatment_sessions RENAME COLUMN price_per_course TO price_per_session;
                END IF;
            END $$""", "rename price_per_course column")
        print("✅ Migrations complete")


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
app.include_router(treatment_sessions.router)


@app.get("/")
def root():
    return {"message": "Clinic Chatbot API is running", "version": "1.0.0", "docs": "/docs"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}