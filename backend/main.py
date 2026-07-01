import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.observability import init_sentry

# Initialize error monitoring before anything else (no-op unless SENTRY_DSN set).
init_sentry()

# Import all models so create_all sees them
import app.models  # noqa — registers all models with Base.metadata for create_all

from app.routers import auth, chat, dashboard, doctors, appointments, leads, superadmin, patients, visits, billing, branches, users, follow_ups, prescriptions, notes, voice, analytics, whatsapp, booking, notifications, doctor_portal, services, rooms, treatment_sessions, reports, import_data, conversations, knowledge, subscription, audit, export, onboarding
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
        # branches — columns added after initial deploy
        _run_sql(conn,
            "ALTER TABLE branches ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Karachi'",
            "branches.timezone")
        _run_sql(conn,
            "ALTER TABLE branches ADD COLUMN IF NOT EXISTS working_hours TEXT",
            "branches.working_hours")
        _run_sql(conn,
            "ALTER TABLE branches ADD COLUMN IF NOT EXISTS bot_name VARCHAR(100)",
            "branches.bot_name")
        _run_sql(conn,
            "ALTER TABLE branches ADD COLUMN IF NOT EXISTS welcome_message TEXT",
            "branches.welcome_message")

        # tenants — columns added after initial deploy
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'starter'",
            "tenants.plan")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bot_name VARCHAR(100) DEFAULT 'ClinicBot'",
            "tenants.bot_name")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS welcome_message TEXT",
            "tenants.welcome_message")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS primary_color VARCHAR(7) DEFAULT '#2563eb'",
            "tenants.primary_color")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(32)",
            "tenants.whatsapp_number")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bot_tone VARCHAR(20) DEFAULT 'warm'",
            "tenants.bot_tone")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                question VARCHAR(500) NOT NULL,
                answer TEXT NOT NULL,
                category VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )""", "create knowledge_base")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_kb_tenant ON knowledge_base (tenant_id)",
            "index knowledge_base.tenant_id")
        # Full-text search index over question + answer (lightweight RAG retrieval)
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_kb_fts ON knowledge_base "
            "USING GIN (to_tsvector('english', question || ' ' || answer))",
            "index knowledge_base full-text")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),
                plan VARCHAR(20) NOT NULL DEFAULT 'starter',
                status VARCHAR(20) NOT NULL DEFAULT 'trialing',
                gateway VARCHAR(20),
                gateway_customer_id VARCHAR(120),
                gateway_subscription_id VARCHAR(120),
                checkout_ref VARCHAR(120),
                pending_plan VARCHAR(20),
                trial_ends_at TIMESTAMPTZ,
                current_period_end TIMESTAMPTZ,
                cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )""", "create subscriptions")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_subs_checkout_ref ON subscriptions (checkout_ref)",
            "index subscriptions.checkout_ref")
        _run_sql(conn,
            "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS human_handling BOOLEAN NOT NULL DEFAULT FALSE",
            "chat_sessions.human_handling")
        _run_sql(conn,
            "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS unread_count INTEGER NOT NULL DEFAULT 0",
            "chat_sessions.unread_count")
        _run_sql(conn,
            "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(50)",
            "chat_sessions.alternate_phone")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(50)",
            "appointments.alternate_phone")
        _run_sql(conn,
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(50)",
            "leads.alternate_phone")

        # doctors — columns added after initial deploy
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id)",
            "doctors.branch_id")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS qualification VARCHAR(255)",
            "doctors.qualification")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS bio TEXT",
            "doctors.bio")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS fee VARCHAR(50)",
            "doctors.fee")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS treatments TEXT[]",
            "doctors.treatments")
        _run_sql(conn,
            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS timings JSONB DEFAULT '[]'",
            "doctors.timings")

        # appointments — columns added after initial deploy
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
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS whatsapp_number_mappings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                branch_id UUID REFERENCES branches(id),
                phone_number_id VARCHAR(64) NOT NULL UNIQUE,
                whatsapp_number VARCHAR(32),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                message_limit_monthly INTEGER NOT NULL DEFAULT 1000,
                messages_used_this_month INTEGER NOT NULL DEFAULT 0,
                limit_reset_date TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT now()
            )""", "create whatsapp_number_mappings")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_wanm_tenant ON whatsapp_number_mappings (tenant_id)",
            "index whatsapp_number_mappings.tenant_id")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS system_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                clinic_id UUID REFERENCES tenants(id),
                report_type VARCHAR(20) NOT NULL,
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                generated_at TIMESTAMPTZ DEFAULT now(),
                metrics JSONB DEFAULT '{}',
                xlsx_path VARCHAR(500),
                pdf_path VARCHAR(500)
            )""", "create system_reports")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_system_reports_clinic ON system_reports (clinic_id)",
            "index system_reports.clinic_id")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS import_mappings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                entity VARCHAR(30) NOT NULL,
                mapping JSONB DEFAULT '{}',
                updated_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT uq_import_mapping_tenant_entity UNIQUE (tenant_id, entity)
            )""", "create import_mappings")
        _run_sql(conn, """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                user_id UUID REFERENCES users(id),
                user_email VARCHAR(255),
                action VARCHAR(20) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(64),
                summary VARCHAR(255),
                "before" JSONB,
                "after" JSONB,
                ip VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT now()
            )""", "create audit_logs")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_audit_tenant_created ON audit_logs (tenant_id, created_at)",
            "index audit_logs.tenant_created")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_logs (entity_type, entity_id)",
            "index audit_logs.entity")
        # Soft-delete bookkeeping: when a record was removed (complements is_active).
        _run_sql(conn,
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            "patients.deleted_at")
        # Knowledge base — provenance for uploaded documents / web pages.
        _run_sql(conn,
            "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'manual'",
            "knowledge_base.source_type")
        _run_sql(conn,
            "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_name VARCHAR(500)",
            "knowledge_base.source_name")
        _run_sql(conn,
            "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_ref UUID",
            "knowledge_base.source_ref")
        _run_sql(conn,
            "CREATE INDEX IF NOT EXISTS ix_kb_source_ref ON knowledge_base (source_ref)",
            "index knowledge_base.source_ref")
        # Follow-ups — automatic reminder agent fields.
        _run_sql(conn,
            "ALTER TABLE follow_ups ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'manual'",
            "follow_ups.kind")
        _run_sql(conn,
            "ALTER TABLE follow_ups ADD COLUMN IF NOT EXISTS channel VARCHAR(20)",
            "follow_ups.channel")
        _run_sql(conn,
            "ALTER TABLE follow_ups ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ",
            "follow_ups.reminder_sent_at")
        _run_sql(conn,
            "ALTER TABLE follow_ups ADD COLUMN IF NOT EXISTS visit_id UUID REFERENCES visit_records(id)",
            "follow_ups.visit_id")
        # Returning-patient tracking: count agent bookings per patient + link
        # each appointment to the patient record it created/matched.
        _run_sql(conn,
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS booking_count INTEGER NOT NULL DEFAULT 0",
            "patients.booking_count")
        _run_sql(conn,
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS last_booking_at TIMESTAMPTZ",
            "patients.last_booking_at")
        _run_sql(conn,
            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patients(id)",
            "appointments.patient_id")
        _run_sql(conn,
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS onboarding_dismissed BOOLEAN NOT NULL DEFAULT FALSE",
            "tenants.onboarding_dismissed")
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
    # Most requests are tiny JSON; cap them at 1MB. Document uploads to the
    # knowledge base are the one exception — allow up to 10MB there.
    DEFAULT_LIMIT = 1_048_576        # 1MB
    UPLOAD_LIMIT = 10_485_760        # 10MB
    UPLOAD_PATHS = ("/knowledge/ingest/document",)

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            limit = (self.UPLOAD_LIMIT
                     if any(request.url.path.startswith(p) for p in self.UPLOAD_PATHS)
                     else self.DEFAULT_LIMIT)
            if int(content_length) > limit:
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
app.include_router(reports.router)
app.include_router(reports.super_router)
app.include_router(import_data.router)
app.include_router(conversations.router)
app.include_router(knowledge.router)
app.include_router(subscription.router)
app.include_router(audit.router)
app.include_router(export.router)
app.include_router(onboarding.router)


@app.get("/")
def root():
    return {"message": "Clinic Chatbot API is running", "version": "1.0.0", "docs": "/docs"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}