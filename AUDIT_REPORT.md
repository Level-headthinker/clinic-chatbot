# AUDIT_REPORT — production readiness audit & fixes

Audit date: 2026-06-12 · Repos: `clinic-chatbot/` + `VIS/`
Every issue below lists severity, status, and (when fixed) where.
**FIXED** = code changed in this pass and covered by a test where practical.

---

## CRITICAL — fixed

### C1. WhatsApp webhook accepted unsigned requests
Anyone who found `/whatsapp/webhook` could inject fake patient messages, burn
Groq quota, create fake bookings/leads, and make the clinic number message
arbitrary people.
**Fix:** `X-Hub-Signature-256` HMAC verification against `META_APP_SECRET`
(`backend/app/routers/whatsapp.py::_verify_meta_signature`); 403 on mismatch.
Blank secret logs a loud warning (dev mode) and is listed as a mandatory
production var. Test: `tests/test_webhook_signature.py`.

### C2. Cross-tenant data leak: unknown number → "first active branch"
`_load_context_for_phone` fell back to the first active branch **in the whole
database** — messages for clinic B could be answered with clinic A's doctors,
fees, address, and bookings written into clinic A's tenant.
**Fix:** fail-closed resolution via the new `whatsapp_number_mappings` table
(phone_number_id → tenant/branch), with legacy exact `branch.phone` match
kept; unregistered numbers get no reply and a log line.
Test: `tests/test_webhook_routing.py`.

### C3. Voice router fully unauthenticated
`POST /voice/outbound` let anyone place AI phone calls on the clinic's VAPI
bill (with partially attacker-controlled first message); `GET /voice/calls`
leaked call records incl. patient numbers; `POST /voice/vapi-llm` was an open
proxy to the Groq API key.
**Fix:** `/outbound` and `/calls` now require an admin user; `/vapi-server` and
`/vapi-llm` require the `X-Vapi-Secret` header matching `VAPI_SERVER_SECRET`
(closed/503 when unset); `/status` requires login.

### C4. Privilege escalation via user management
`require_admin_user` includes branch admins, and the users router let a branch
admin update/reset-password/deactivate **any** user in the tenant — including
the clinic owner — and grant `role="admin"` with tenant-level access.
**Fix:** `_require_manage_scope` (branch admins manage only their own branch)
and `_require_role_grant_allowed` (only tenant-level admins grant admin), plus
a block on re-homing users out of the admin's branch.
Test: `tests/test_data_isolation.py::TestRoleScoping`.

### C5. `/whatsapp/call/turn` open when VIS_API_KEY blank
"Optional auth" defaulted to no auth — anyone could converse and book as any
caller. **Fix:** endpoint now returns 503 when no key is configured and uses
constant-time comparison when it is.

### C6. Public booking accepted any datetime, unthrottled
`/public/clinic/{slug}/book` wrote arbitrary datetimes (3 AM, past dates) into
the diary and had no rate limit — a script could flood a clinic with junk.
**Fix:** `_slot_is_offered` validates future + working day + working hours +
30-minute grid + not already booked; Pakistani phone format validation;
10 requests/hour/IP rate limit. Test: `tests/test_booking_validation.py`.

---

## HIGH — fixed

### H1. Voice notes spoke with Deepgram's robotic voice instead of ElevenLabs Sarah (VIS)
Root cause chain (all three fixed):
1. `TTS_PROVIDER=router` routed **English → Deepgram** and only Urdu →
   ElevenLabs; with `WHATSAPP_VOICE_LANGS=en` (default) every voice note was
   Deepgram Aura. → Router now uses **ElevenLabs for ALL languages**; Deepgram
   is a logged fallback only (key missing or ElevenLabs call fails).
2. `ElevenLabsTTS` ignored `audio_format="ogg_opus"` and always returned mp3 —
   WhatsApp shows mp3 as a file attachment, not a native voice-note bubble.
   → Now requests native Opus (`opus_48000_64`); falls back to mp3 + **ffmpeg**
   conversion (`VIS/app/core/audio.py`); last resort delivers mp3.
3. `.env` had `ELEVENLABS_MODEL=eleven_flash_v2_5` → switched to
   `eleven_multilingual_v2` (better Urdu pronunciation). Voice ID was already
   Sarah (`EXAVITQu4vr4xnSDxMaL`); the `.env.example` default (Rachel) updated.
Also: production boot now **fails fast** if TTS is elevenlabs/router with no
`ELEVENLABS_API_KEY`. Deepgram remains STT-free (VIS STT is Groq Whisper).
Tests: `VIS/tests/test_tts_routing.py` (5 tests). Full VIS suite: 43 passed.

### H2. No per-clinic message limits / usage tracking
**Fix:** `whatsapp_number_mappings.message_limit_monthly` +
`messages_used_this_month` with auto month rollover, enforced in the webhook
(grace message to the patient exactly at the limit, silent drop after).
Superadmin APIs: list/register/toggle numbers, `PUT .../limit`,
`GET /super/clinics/{id}/message-stats`. Clinic API: `GET /whatsapp/usage`.
Monthly reset cron as safety net. Test: `tests/test_webhook_routing.py::TestMessageQuota`.

### H3. Instant-booking bug: "book" counted as a confirmation
`is_confirmation_message` used substring matching with "book"/"ok" in the
list — *"I want to book an appointment"* from a returning patient booked the
top slot immediately, without showing options ("ok" also fired inside
"looking"/"booked"). **Fix:** word-boundary regex; "book" removed from
confirmations. Test: `tests/test_confirmation_and_language.py`.

### H4. Stale DB connections → 500s after idle/restart
**Fix:** `pool_pre_ping=True`, `pool_recycle=1800`, explicit pool sizing in
`backend/app/database.py`.

---

## MEDIUM — fixed

- **M1. Language flip mid-conversation:** a digit-only message (phone number)
  reset Urdu chats to English. `detect_language` now takes a fallback; the
  brain passes the session language; the LLM language-lock uses the same value.
- **M2. Login user-enumeration timing oracle:** bcrypt now runs on a dummy
  hash when the email doesn't exist; emails normalized to lowercase on
  register and login.
- **M3. Staff could read security flags:** `/super/my-clinic/security/*` used
  `get_current_user`; now `require_admin_user` (flag content includes patient
  message text).
- **M4. Guard misclassification:** "You are now DAN" flagged as
  `role_override` instead of `jailbreak` (pattern ordering) — jailbreak names
  now checked first. (Pre-existing failing test now passes.)
- **M5. Output truncation overshot its own cap:** truncation appended a
  99-char suffix *after* cutting at the 800-char limit and could end
  mid-gibberish. Now always ≤ cap, ends at a sentence boundary or "...".
  (Two pre-existing failing tests now pass.)

## NEW FEATURES delivered in this pass

1. **Reports (Phase 9 + extension)** — `system_reports` table **with
   `clinic_id`**; daily/weekly/monthly/yearly metrics per clinic and
   platform-wide: messages, appointments booked / completed / no-show,
   busiest doctor, busiest time slot, new vs returning patients, leads,
   revenue (billed/collected from invoices), daily breakdown.
   Endpoints: `GET /reports/clinic` (+`/history`),
   `GET /reports/{id}/download?format=pdf|xlsx` (branded, server-side,
   cached on disk for re-download), `GET /super-reports/platform`,
   `GET /super-reports/clinics` (drill-down). Cron: weekly (Mon 08:00 PKT) and
   monthly (1st 08:00 PKT) auto-generation with exports pre-rendered.
2. **3-step import with fuzzy column mapping (Phase 8)** — for patients,
   doctors, staff, services, appointments:
   `POST /import/{entity}/preview` (headers + 5 sample rows + rapidfuzz
   suggestions; ≥80% auto-applied, below shown as suggestion only; saved
   per-clinic mapping pre-fills next time) →
   frontend mapping screen (required fields enforced server-side) →
   `POST /import/{entity}/commit` (dry_run validate-only supported;
   plain-language row-by-row errors; valid rows imported transactionally;
   failed rows returned as a downloadable CSV; duplicates skipped by
   phone/name/email). Staff import auto-generates temp passwords.
   Tests: `tests/test_import_mapping.py`.

## OPEN — known gaps (not fixed in this pass, in priority order)

| # | Severity | Issue |
|---|---|---|
| O1 | HIGH | Rate limiters and webhook de-dup are in-process memory — broken with >1 worker/replica and proxy-blind (`request.client.host` is the proxy on Render). Adopt Redis (VIS already supports `REDIS_URL` for sessions/de-dup) and run uvicorn with `--proxy-headers`. |
| O2 | HIGH | Single global `META_ACCESS_TOKEN`/`META_PHONE_NUMBER_ID` for sending. The mapping table fixes **routing**, but per-clinic *sending* credentials should move onto the mapping row (encrypted) so 50 clinics can have 50 numbers under one Meta app. |
| O3 | HIGH | Slot generation uses naive server time (UTC on Render) while branches have an unused `timezone` column — slots/reminders shift 5h for Asia/Karachi clinics. Needs a tz-aware refactor of `generate_doctor_slots`/scheduler. |
| O4 | MED | JWT: single 60-min access token, no refresh token, logout is client-side. Target: 15-min access + 7-day httpOnly refresh. |
| O5 | MED | Token kept in localStorage *and* a SameSite=None cookie — pick one strategy + CSRF token. |
| O6 | MED | `requirements.txt` largely unpinned (new deps pinned); pin all + lockfile. |
| O7 | MED | PHI posture: no audit log of admin actions, no retention/deletion policy for chat transcripts, voice media not explicitly deleted post-transcription (VIS processes in memory; Meta hosts media). |
| O8 | LOW | `print()` logging in older clinic-chatbot routers (new/edited code uses `logging`); add Sentry. |
| O9 | LOW | Postgres RLS as a second isolation layer (`SET app.current_clinic_id`) — designed but not enabled; all queries are ORM-scoped by tenant_id today. |
| O10 | LOW | Google Calendar integration, doctor-portal bulk features, receptionist UX simplification, WebSocket live inbox — net-new feature work, untouched. |

## Structural Changes Required (flagged for confirmation — NOT done)

1. **`backend/app/routers/admin.py` is dead, broken code** (no imports, no
   router object; crashes if ever imported; not registered). Recommend delete.
2. **`backend/app/routers/treatment_courses.py` + `models/treatment_course.py`
   (untracked)** duplicate the registered `treatment_sessions` pair and map to
   the old `treatment_courses` table, which `create_all` re-creates after the
   startup migration renames it. Recommend delete both files.
3. **Startup `_add_missing_columns` vs Alembic**: both exist; runtime DDL is
   the de-facto migration path. New tables in this pass were added to *both*
   (runtime DDL + Alembic revision `a7b3c9d1e2f4`) per the
   structure-preservation instruction, but long-term one path should win
   (recommend Alembic, run on deploy).
