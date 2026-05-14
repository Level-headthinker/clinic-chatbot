# ClinicBot

AI-powered, multi-tenant clinic chatbot and clinic management platform for Pakistan's healthcare market.

ClinicBot combines a patient-facing AI chat widget with a clinic admin dashboard. Patients can ask questions, share their details, and request appointments in English, Urdu, or Roman Urdu. Clinic staff can manage doctors, appointments, leads, patient records, visits, and billing from a React dashboard backed by a FastAPI API and PostgreSQL database.

This README is based on:

- `project_snapshot.json` - current codebase snapshot: 59 files, 8462 lines
- `clinicbot_master_document.docx` - product specification, database roadmap, and audit notes

## Current Status

The project is a functional prototype with the core multi-tenant API, React dashboard, chatbot flow, patient records, visits, billing, and super-admin screens started. It is not production-ready yet. The master specification identifies required database migrations, security fixes, and workflow improvements that must be completed before deployment.

## Implemented Features

### Platform Foundation

- FastAPI backend application with `/health` and API docs
- PostgreSQL integration through SQLAlchemy
- Pydantic settings loaded from `backend/.env`
- Automatic table creation with `Base.metadata.create_all(bind=engine)`
- Render deployment config for the backend in `render.yaml`
- Multi-tenant data model using `tenant_id` across doctors, appointments, leads, chat sessions, patients, visits, and invoices
- UUID primary keys across core models
- Soft-delete style `is_active` flags on major tables

### Authentication and Tenant Registration

- Clinic registration endpoint: `POST /auth/register`
- Login endpoint: `POST /auth/login`
- JWT token creation and validation
- Password hashing with `bcrypt`
- Protected dashboard API routes using `get_current_user`
- React auth context with token storage and authenticated Axios requests
- Full `/auth/me` user profile endpoint
- Login check for `tenant.is_active`
- Super-admin authorization via database role instead of hardcoded email

### AI Chatbot

- Chat endpoint: `POST /chat/message`
- Chat session lookup: `GET /chat/session/{session_token}`
- Groq LLM integration using `llama-3.1-8b-instant`
- Language detection for English, Urdu script, and Roman Urdu
- Emergency keyword detection with 1122 response
- Conversation history stored in `chat_sessions.messages`
- Last 10 messages sent to the LLM for context
- Patient name and phone extraction through LLM helper
- Returning patient detection from appointments and patient records
- Auto lead capture after name and phone are collected
- Appointment creation after user confirmation
- Real appointment slot picker from doctor timings
- Specialty and treatment matching before choosing a doctor
- WhatsApp Business / Twilio integration
- Public production-ready embeddable widget script

### Admin Dashboard

- React app using Create React App
- Login and register pages
- Protected dashboard routes
- Sidebar navigation
- Dashboard overview page
- Doctors page
- Appointments page
- Leads page
- Chat preview page
- Patients page
- Patient detail page
- Billing page
- Super-admin page
- User-facing error states across all pages
- Urdu dashboard mode
- Advanced analytics dashboard

### Doctors

- Doctor model with name, specialty, qualification, bio, fee, treatments, timings, and available slots
- Doctor CRUD router
- Per-tenant doctor filtering
- Active/inactive doctor support
- Real availability generation from `doctor.timings`
- Specialty matching during chatbot booking

### Appointments

- Appointment model with doctor, patient details, slot, status, and notes
- Public appointment booking endpoint: `POST /appointments/book`
- Authenticated appointment listing
- Authenticated appointment status update
- Authenticated appointment cancellation
- Slot conflict check for the same doctor and slot
- Authentication and tenant ownership enforcement on `POST /appointments/book`
- Database status constraint for valid appointment states
- `no_show` status support in API validation
- Dashboard filters by date and doctor
- Automated patient reminders

### Leads

- Lead model with name, phone, concern, source, status, and notes
- Lead auto-capture from chatbot
- Lead status update support
- Lead stats endpoint
- Lead conversion when chatbot appointment is confirmed
- Database status constraint for valid lead states
- Optimized lead stats query using grouped aggregation

### Patient Records and Visits

-  Patient model with name, phone, age, gender, blood group, allergies, chronic conditions, and emergency contact
-  Patient create, list, lookup, detail, update, and soft delete routes
-  Visit record model with complaint, diagnosis, prescription JSON, tests, notes, next visit date, and fee
-  Visit create, list by patient, detail, and update routes
-  Tenant filtering for patient and visit access
-  Structured prescription items accepted by the API
-  Search by CNIC
-  Printable prescription PDF
-  Follow-up workflow based on `next_visit_date`
-  Legacy data import from Excel/CSV
-  Per-clinic custom patient and visit fields

### Billing

-  Invoice model with consultation fee, additional charges, total amount, paid amount, payment status, and payment method
-  Invoice creation route
-  Invoice list and detail routes
-  Billing stats endpoint
-  Payment update route
-  Add charge route
-  Soft-delete invoice route
-  Auto invoice creation when a visit has a fee
-  Unique invoice number constraint per tenant
-  Race-condition-proof invoice number generation
-  CSV/PDF export for accounting
-  Payment status database constraint

### Super Admin

-  Super-admin stats endpoint
-  Clinic listing across tenants
-  Clinic activate/deactivate endpoint
-  Clinic plan update endpoint
-  Super-admin check backed by `users.is_superadmin`
-  Remove hardcoded `admin@cityclinic.com`
-  Optimize clinic stats to avoid N+1 queries

## Pending Features From The Product Spec

-  Multi-branch tenant hierarchy with main branch and branch-level access
-  Branch-scoped staff roles and permissions
-  Main branch dashboard with consolidated branch data
-  Dynamic custom fields for patients, visits, and appointments
-  Tenant-managed custom field schema UI
-  Legacy Excel/CSV import with field mapping and import logs
-  Audit log table for create, update, delete, and view events
-  Notifications table and queue for email, WhatsApp, and SMS
-  WhatsApp chatbot channel
-  AI call answering
-  Patient portal
-  Prescription PDF output
-  Bulk SMS reminders
-  Analytics V2: busiest hours heatmap, doctor performance, seasonal trends, patient growth
-  Rate limiting on `/auth/login`
-  Production HTTPS and domain validation

## Database Changes Still Required

The spec requires these changes through Alembic migrations before production. Do not apply them manually in pgAdmin on a production database.

### Required Indexes

-  `appointments(patient_phone, tenant_id)` for returning-patient and chatbot lookup
-  `appointments(tenant_id, status)` for dashboard filtering
-  Unique `chat_sessions(session_token)` index
-  `chat_sessions(tenant_id)` index
-  `leads(phone, tenant_id)` for duplicate prevention
-  `patients(phone, tenant_id)` for patient lookup
-  `audit_logs(tenant_id, created_at DESC)` after audit logs are added

Example migration shape:

```python
from alembic import op


def upgrade():
    op.create_index("ix_appt_phone_tenant", "appointments", ["patient_phone", "tenant_id"])
    op.create_index("ix_appt_tenant_status", "appointments", ["tenant_id", "status"])
    op.create_index("ix_chat_token", "chat_sessions", ["session_token"], unique=True)
    op.create_index("ix_chat_tenant", "chat_sessions", ["tenant_id"])
    op.create_index("ix_lead_phone_tenant", "leads", ["phone", "tenant_id"])
    op.create_index("ix_patient_phone_tenant", "patients", ["phone", "tenant_id"])
```

### Super-Admin Column

-  Add `users.is_superadmin BOOLEAN NOT NULL DEFAULT FALSE`
-  Migrate the real platform admin user to `is_superadmin = TRUE`
-  Replace hardcoded email authorization in `backend/app/routers/superadmin.py`

```sql
ALTER TABLE users
ADD COLUMN is_superadmin BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE users
SET is_superadmin = TRUE
WHERE email = 'admin@cityclinic.com';
```

### Invoice Constraint and Number Generation

-  Add unique invoice number constraint per tenant
-  Replace count-based invoice numbers with a sequence or UUID suffix
-  Update both `visits.py` and `billing.py`

```sql
ALTER TABLE invoices
ADD CONSTRAINT uq_invoice_number_tenant UNIQUE (invoice_number, tenant_id);
```

### Branch Support

-  Add parent-child tenant relationship
-  Add branch level marker
-  Update query helpers so main branches can see sub-branches and branch tenants only see themselves

```sql
ALTER TABLE tenants
ADD COLUMN parent_tenant_id UUID REFERENCES tenants(id) DEFAULT NULL;

ALTER TABLE tenants
ADD COLUMN branch_level VARCHAR(20) NOT NULL DEFAULT 'main';
```

### Status Constraints

-  Add appointment status check constraint
-  Add lead status check constraint
-  Add payment status check constraint for invoices

```sql
ALTER TABLE appointments
ADD CONSTRAINT chk_appointment_status
CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show'));

ALTER TABLE leads
ADD CONSTRAINT chk_lead_status
CHECK (status IN ('new', 'contacted', 'converted', 'lost'));
```

### Custom Fields

-  Add `custom_fields JSONB DEFAULT '{}'` to `patients`
-  Add `custom_fields JSONB DEFAULT '{}'` to `visit_records`
-  Add `custom_fields JSONB DEFAULT '{}'` to `appointments`
-  Add `tenant_field_schemas` table for per-clinic field definitions
-  Update frontend forms to render schema-driven custom fields

```sql
ALTER TABLE patients ADD COLUMN custom_fields JSONB DEFAULT '{}';
ALTER TABLE visit_records ADD COLUMN custom_fields JSONB DEFAULT '{}';
ALTER TABLE appointments ADD COLUMN custom_fields JSONB DEFAULT '{}';
```

### Legacy Import and Audit Tables

-  Add `data_imports` table
-  Add `patients.import_source`
-  Add `patients.original_data JSONB DEFAULT '{}'`
-  Add `audit_logs` table
-  Add `notifications` table

## Code Fixes Still Needed Before Production

### Security Blockers

-  Restrict CORS in `backend/main.py`
  - Current code uses `allow_origins=["*"]`
  - Replace with explicit frontend domains from environment config
-  Add authentication to `POST /appointments/book`
  - Current endpoint accepts `tenant_id` from the request body
  - It should derive tenant ownership from JWT or a safe public booking token design
-  Replace hardcoded super-admin email in `backend/app/routers/superadmin.py`
  - Current code uses `SUPER_ADMIN_EMAIL = "admin@cityclinic.com"`
  - Use `users.is_superadmin`
-  Remove debug logs from `frontend/src/pages/ChatPreview.jsx`
  - Current logs print user context, localStorage data, request payloads, and API responses
-  Remove commented duplicate auth implementation from `backend/app/services/auth.py`
-  Check `tenant.is_active` during login in `backend/app/routers/auth.py`
-  Add rate limiting to `/auth/login`
-  Ensure `.env` files are never committed

### Booking and Chat Fixes

-  Replace hardcoded chatbot booking slot in `backend/app/routers/chat.py`
  - Current slot is tomorrow at 10:00 AM
  - Use `doctor.timings`, existing appointments, and available slot generation
-  Match doctors by specialty/treatments before fallback
-  Return explicit available slots and ask for confirmation before saving
-  Review `GET /chat/session/{session_token}` privacy because it currently does not require auth

### Data Integrity and Performance Fixes

-  Add invoice uniqueness and race-safe invoice numbers
-  Replace mutable Pydantic defaults like `[]` with `Field(default_factory=list)`
-  Optimize super-admin clinic stats to avoid N+1 queries
-  Optimize lead stats with a grouped query
-  Replace `print()` in email service with structured logging
-  Replace `datetime.utcnow()` with timezone-aware timestamps
-  Decide on one sync/async SQLAlchemy strategy

### Frontend Fixes

-  Remove hardcoded chat fallback slug `city-clinic`
-  Add user-facing errors instead of only `console.error`
-  Confirm `App.js` and `App.jsx` duplication is intentional
-  Protect the super-admin frontend route
-  Add frontend views for custom fields, imports, branch management, and advanced analytics

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Python |
| API Server | Uvicorn |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Settings | Pydantic Settings, python-dotenv |
| Auth | JWT with `python-jose`, bcrypt |
| AI / LLM | Groq API, LLaMA model |
| Email | Gmail SMTP via `smtplib` |
| Frontend | React 19, Create React App |
| Routing | React Router |
| HTTP Client | Axios |
| Icons | lucide-react |
| Testing Libraries | React Testing Library, Jest setup from CRA |
| Deployment | Render backend service via `render.yaml` |

## Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/clinic_chatbot
SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
MAIL_EMAIL=your-gmail-address@gmail.com
MAIL_PASSWORD=your-gmail-app-password
ADMIN_EMAIL=clinic-admin@example.com
```

Create `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8000
```

Notes:

- `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY` are required by the backend settings.
- `MAIL_EMAIL`, `MAIL_PASSWORD`, and `ADMIN_EMAIL` are needed for booking and lead notification emails.
- Use a Gmail App Password for `MAIL_PASSWORD`, not a normal Gmail login password.
- Never commit `.env` files.

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Groq API key

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API root: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Database

```sql
CREATE DATABASE clinic_chatbot;
```

Tables are currently created automatically when the backend starts. For production, replace automatic schema creation with Alembic migrations.

### Frontend

```bash
cd frontend
npm install
npm start
```

Frontend URL:

- `http://localhost:3000`

### First Clinic Registration

Use the API docs or an HTTP client to call `POST /auth/register`:

```json
{
  "clinic_name": "City Clinic",
  "clinic_slug": "city-clinic",
  "admin_email": "admin@cityclinic.com",
  "admin_password": "change-this-password",
  "admin_full_name": "Clinic Admin"
}
```

Then log in at `http://localhost:3000/login`.

## Project Folder Structure

```text
clinic-chatbot/
+-- README.md
+-- render.yaml
+-- project_snapshot.json
+-- project_to_json.py
+-- clinicbot_master_document.docx
+-- backend/
|   +-- main.py
|   +-- requirements.txt
|   +-- app/
|       +-- config.py
|       +-- database.py
|       +-- models/
|       |   +-- appointment.py
|       |   +-- chat.py
|       |   +-- doctor.py
|       |   +-- invoice.py
|       |   +-- patient.py
|       |   +-- tenant.py
|       |   +-- user.py
|       |   +-- visit.py
|       +-- routers/
|       |   +-- admin.py
|       |   +-- appointments.py
|       |   +-- auth.py
|       |   +-- billing.py
|       |   +-- chat.py
|       |   +-- doctors.py
|       |   +-- leads.py
|       |   +-- patients.py
|       |   +-- superadmin.py
|       |   +-- visits.py
|       +-- services/
|           +-- auth.py
|           +-- email.py
|           +-- llm.py
+-- frontend/
    +-- package.json
    +-- public/
    |   +-- index.html
    |   +-- widget.html
    +-- src/
        +-- api/
        |   +-- axios.js
        +-- components/
        |   +-- Sidebar.jsx
        +-- context/
        |   +-- AuthContext.jsx
        +-- pages/
        |   +-- Appointments.jsx
        |   +-- Billing.jsx
        |   +-- ChatPreview.jsx
        |   +-- Dashboard.jsx
        |   +-- Doctors.jsx
        |   +-- Leads.jsx
        |   +-- Login.jsx
        |   +-- PatientDetail.jsx
        |   +-- Patients.jsx
        |   +-- Register.jsx
        |   +-- SuperAdmin.jsx
        +-- App.js
        +-- App.jsx
        +-- index.js
        +-- index.css
```

## Production Readiness Checklist

-  Add Alembic and convert schema changes into migrations
-  Apply required indexes and constraints
-  Add `users.is_superadmin`
-  Lock down CORS
-  Fix unauthenticated appointment booking
-  Remove debug logs and dead auth code
-  Implement real slot selection
-  Make invoice numbers unique and concurrency-safe
-  Add branch support
-  Add custom fields and legacy import
-  Add audit logs and notification queue
-  Add rate limiting and production logging
-  Run backend and frontend tests before deployment
