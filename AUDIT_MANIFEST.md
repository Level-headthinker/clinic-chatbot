# AUDIT_MANIFEST — files read during this audit

Audit date: 2026-06-12 · Scope: `clinic-chatbot/` (backend + frontend auth layer) and `VIS/`

## clinic-chatbot — backend (read in full)

| File | Notes |
|---|---|
| backend/main.py | App entrypoint, runtime migrations, middleware, router registration |
| backend/app/config.py | Settings (pydantic-settings) |
| backend/app/database.py | Engine/session setup |
| backend/app/models/__init__.py | Model registry |
| backend/app/models/appointment.py | incl. partial unique index for double-booking |
| backend/app/models/chat.py | ChatSession + Lead |
| backend/app/models/patient.py | |
| backend/app/models/doctor.py | |
| backend/app/models/invoice.py | revenue source for reports |
| backend/app/routers/auth.py | register/login/me, rate limiting, cookies |
| backend/app/routers/chat.py | web chat endpoint + guard wiring |
| backend/app/routers/whatsapp.py | webhook, voice notes, call/turn |
| backend/app/routers/voice.py | VAPI integration (was fully unauthenticated) |
| backend/app/routers/booking.py | public self-booking |
| backend/app/routers/superadmin.py | platform admin + security flags |
| backend/app/routers/users.py | staff management (privilege-escalation fix) |
| backend/app/routers/doctor_portal.py | doctor-scoped queries (first 80 lines) |
| backend/app/routers/treatment_courses.py | untracked duplicate (see Structural Changes) |
| backend/app/routers/admin.py | dead/broken fragment (see Structural Changes) |
| backend/app/services/auth.py | hashing, JWT, role dependencies |
| backend/app/services/conversation.py | shared booking brain |
| backend/app/services/llm.py | prompt, language/intent detection, Groq calls |
| backend/app/services/input_guard.py | sanitize/length/rate/injection |
| backend/app/services/output_guard.py | emergency/medical/length/disclaimer (key sections) |
| backend/app/services/email.py | SMTP notifications (first 80 lines) |
| backend/app/services/scheduler.py | APScheduler jobs |
| backend/app/services/messaging.py | outbound WhatsApp/SMS (first 60 lines) |
| backend/tests/conftest.py | fixture style (fakes, no DB) |
| backend/tests/test_output_guard.py | length-cap section |
| backend/tests/test_input_guard.py | injection section |
| backend/requirements.txt | unpinned (flagged) |
| backend/alembic/versions/* | listed; latest revision format read |
| backend/.env | key presence only — values never echoed |

## clinic-chatbot — frontend

| File | Notes |
|---|---|
| frontend/src/api/axios.js | token handling, 401 interceptor |
| frontend/src/context/AuthContext.jsx | session refresh flow (first 60 lines) |

## clinic-chatbot — infra

| File | Notes |
|---|---|
| docker-compose.yml | |
| .env.example | |
| .gitignore | confirmed .env not tracked |

## VIS — voice service (read in full unless noted)

| File | Notes |
|---|---|
| app/config.py | provider selection, production validation |
| app/main.py | lifespan, CORS |
| app/core/pipeline.py | STT → LLM → TTS flow |
| app/core/http.py | shared client + retry/backoff |
| app/providers/__init__.py | provider registry |
| app/providers/tts_router.py | **root cause of robotic voice** |
| app/providers/tts_elevenlabs.py | mp3-only output (fixed) |
| app/providers/tts_deepgram.py | |
| app/routers/voice.py | REST surface, auth, rate limit |
| app/routers/whatsapp.py | signature-verification section (grep-verified) |
| tests/test_registry.py | test style reference |
| .env.example | |
| .env | provider/model lines + key presence only |

## Not read (out of scope this pass)

clinic-chatbot routers: analytics, appointments, billing, branches, dashboard,
doctors, follow_ups, leads, notes, notifications, patients, prescriptions,
rooms, services, settings, treatment_sessions, visits (auth-guard presence
verified by grep — all use `get_current_user`/`require_*`); frontend pages
beyond the auth layer; VIS `agent/`, `call-agent/`, `scripts/`.
