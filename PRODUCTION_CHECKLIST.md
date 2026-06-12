# PRODUCTION_CHECKLIST — before serving real clinics

Items marked ✅ are enforced by code after this audit; ☐ are operator actions.

## Security — env & config
- ☐ `META_APP_SECRET` set (clinic-chatbot) — webhook signature verification activates automatically; without it the check is SKIPPED (logged warning)
- ☐ `VAPI_SERVER_SECRET` set if using the VAPI voice agent (endpoints are closed/503 until set) — configure the same value as a custom header in the VAPI dashboard
- ☐ `VIS_API_KEY` set on both clinic-chatbot and VIS (`/whatsapp/call/turn` is closed until set)
- ☐ VIS: `ENV=production` (refuses to boot with blank `API_KEY`, blank `META_APP_SECRET` while WhatsApp creds set, or blank `ELEVENLABS_API_KEY` while TTS=router/elevenlabs) ✅ enforced at boot
- ☐ `SECRET_KEY` ≥ 32 random chars; rotate any value that was ever committed/shared
- ☐ `CORS_ORIGINS` = exact production domains only
- ☐ `DATABASE_URL` uses `?sslmode=require` on hosted Postgres
- ☐ Run `alembic upgrade head` (new revision `a7b3c9d1e2f4`) — or rely on startup DDL (both paths create the new tables)
- ✅ Login/registration/chat/public-booking rate limits (in-process — see Scale)
- ✅ Public booking validates slots against the doctor's real schedule
- ✅ Branch admins cannot escalate to tenant admin or touch other branches

## WhatsApp multi-clinic routing
- ☐ For EVERY clinic number: register it via `POST /super/whatsapp/numbers` (phone_number_id → clinic/branch, monthly limit)
- ✅ Unregistered numbers are ignored (fail closed — no cross-tenant replies)
- ✅ Monthly limits enforced with patient grace message; counters auto-reset; superadmin `GET /super/clinics/{id}/message-stats`; clinic `GET /whatsapp/usage`
- ☐ Per-clinic Meta access tokens (open item O2) if clinics use separate WABAs

## Voice (VIS)
- ☐ `ELEVENLABS_API_KEY` set; voice = Sarah `EXAVITQu4vr4xnSDxMaL`, model = `eleven_multilingual_v2` ✅ defaults
- ☐ Install **ffmpeg** on the VIS host (voice-note bubbles; without it replies degrade to mp3 audio files — logged once)
- ☐ Set `REDIS_URL` on VIS before running >1 replica (sessions + webhook de-dup)
- ✅ English AND Urdu replies use ElevenLabs; Deepgram only as logged fallback

## Performance & scale
- ✅ DB pool: pre-ping + 30-min recycle
- ☐ Run uvicorn with `--proxy-headers --forwarded-allow-ips='*'` (Render/nginx) so rate limits see real client IPs
- ☐ Move clinic-chatbot rate limits + webhook de-dup to Redis before >1 worker (open item O1)
- ☐ DB indexes exist on tenant_id/phone_number_id/created_at for new tables ✅ (migration)

## Monitoring & ops
- ☐ Error tracking (Sentry) on both services
- ☐ Uptime monitor on `/health` (clinic-chatbot) and `/health` (VIS)
- ☐ Daily automated Postgres backups + one tested restore
- ☐ Log aggregation; alert on `WhatsApp webhook rejected: bad or missing signature` spikes (attack signal)

## Reports & data
- ✅ Weekly (Mon 08:00 PKT) and monthly (1st 08:00 PKT) per-clinic reports auto-generate with cached PDF/XLSX
- ☐ Mount/persist `reports_store/` (or set `REPORTS_DIR`) on the host so re-downloads survive restarts
- ☐ Define a retention policy for chat transcripts & flagged logs (PHI)

## Testing
- ✅ `pytest tests/ -W ignore` → 156 passed, 1 skipped (clinic-chatbot)
- ✅ `pytest tests/` → 43 passed (VIS)
- ☐ Run the opt-in isolation test against a disposable DB: `TEST_DATABASE_URL=postgresql://… pytest tests/test_data_isolation.py`
- ☐ Load test: 100 concurrent webhook messages (after Redis move)
