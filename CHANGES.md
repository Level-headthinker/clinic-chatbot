# CHANGES — every file modified/created in this pass, with reason

Date: 2026-06-12

## VIS/

| File | Change | Reason |
|---|---|---|
| app/providers/tts_router.py | **Rewritten routing** | ElevenLabs (Sarah) is now primary for ALL languages; Deepgram demoted to logged fallback (key missing / call failed). Was: English→Deepgram = the robotic voice bug. |
| app/providers/tts_elevenlabs.py | Honor `ogg_opus`; full voice_settings | Native Opus from ElevenLabs for WhatsApp voice-note bubbles; mp3+ffmpeg fallback; style/speaker_boost added. |
| app/core/audio.py | **New** | `mp3_to_ogg_opus` ffmpeg helper (probed once, graceful when ffmpeg missing). |
| app/config.py | Comments + production validation | Boot fails in production if TTS=elevenlabs/router without `ELEVENLABS_API_KEY`; `WHATSAPP_VOICE_LANGS` default now `en,ur,ur-roman`. |
| .env | `ELEVENLABS_MODEL` → `eleven_multilingual_v2` | Better Urdu pronunciation (was flash_v2_5). |
| .env.example | Updated TTS section | Sarah voice ID as default; new router semantics documented. |
| tests/test_tts_routing.py | **New** (5 tests) | Guards the robotic-voice regression. |

## clinic-chatbot/backend — security fixes

| File | Change | Reason |
|---|---|---|
| app/routers/whatsapp.py | Signature verification, fail-closed clinic routing, message quotas, `/call/turn` closed-by-default, `GET /whatsapp/usage` | CRITICAL C1, C2, C5, H2 (see AUDIT_REPORT). |
| app/routers/voice.py | Auth on all endpoints | CRITICAL C3 — outbound calls/records/LLM proxy were public. `X-Vapi-Secret` gate for VAPI callbacks. |
| app/routers/users.py | Branch-scope + role-grant guards | CRITICAL C4 — branch-admin privilege escalation. |
| app/routers/booking.py | Slot validation, phone validation, rate limit | CRITICAL C6 — arbitrary datetimes + flooding. |
| app/routers/superadmin.py | Number-mapping CRUD + message-stats endpoints; my-clinic flag endpoints now admin-only | H2 management surface; M3. |
| app/routers/auth.py | Dummy-hash on unknown email; lowercase emails | M2 timing oracle + duplicate-case accounts. |
| app/services/auth.py | *(unchanged)* | — |
| app/config.py | `META_APP_SECRET`, `VAPI_SERVER_SECRET` | New secrets for C1/C3. |
| app/database.py | `pool_pre_ping`, `pool_recycle`, pool sizing | H4 stale connections. |

## clinic-chatbot/backend — bug fixes

| File | Change | Reason |
|---|---|---|
| app/services/conversation.py | Word-boundary confirmation regex (drop "book"); pass session language to detection + LLM | H3 instant-booking; M1 language flip. |
| app/services/llm.py | `detect_language(…, fallback)`; `get_ai_response(…, language=)` | M1. |
| app/services/input_guard.py | Jailbreak patterns checked before role_override | M4 — fixes pre-existing failing test `test_DAN_blocked`. |
| app/services/output_guard.py | Truncation always ≤ cap, sentence boundary or "..." | M5 — fixes two pre-existing failing tests. |

## clinic-chatbot/backend — new features

| File | Change | Reason |
|---|---|---|
| app/models/whatsapp_number.py | **New** `WhatsAppNumberMapping` | phone_number_id → clinic routing + monthly limits (Wati/respond.io pattern). |
| app/models/system_report.py | **New** `SystemReport` (with `clinic_id`) | Phase 9 + per-clinic reports extension. |
| app/models/import_mapping.py | **New** `ImportMapping` | Saved per-clinic column mappings. |
| app/models/__init__.py | Register new models | create_all visibility. |
| app/services/reports.py | **New** | Metric aggregation, branded XLSX (openpyxl) + PDF (reportlab) exports, cached files, cron entrypoint. |
| app/routers/reports.py | **New** | Clinic endpoints (+history, download) and superadmin platform/drill-down endpoints. |
| app/routers/import_data.py | **New** | 3-step import: preview → mapping (rapidfuzz, ≥80% auto) → validate/commit; failed-rows CSV; mapping persistence. |
| app/services/scheduler.py | 3 new cron jobs | Monthly counter reset; weekly (Mon 08:00) + monthly (1st 08:00) report generation. |
| main.py | Register reports/import routers; runtime DDL for 3 new tables | Follows the project's established startup-migration pattern. |
| alembic/versions/a7b3c9d1e2f4_… | **New migration** | Same 3 tables via the proper migration path. |
| requirements.txt | + openpyxl, reportlab, rapidfuzz (pinned `>=`) | Exports + fuzzy matching. |

## clinic-chatbot — tests (new)

| File | Covers |
|---|---|
| tests/test_webhook_signature.py | C1 — 6 cases |
| tests/test_webhook_routing.py | C2 fail-closed + H2 quotas — 6 cases |
| tests/test_booking_validation.py | C6 — 8 cases |
| tests/test_confirmation_and_language.py | H3 + M1 — 9 cases |
| tests/test_import_mapping.py | Import flow — 10 cases |
| tests/test_data_isolation.py | C4 role scoping (7 cases) + opt-in Postgres isolation test (`TEST_DATABASE_URL`) |

## Misc

| File | Change |
|---|---|
| .env.example | `META_APP_SECRET`, `VAPI_SERVER_SECRET` documented |
| .gitignore | `reports_store/` (cached report exports) |

**Not changed (structure preservation):** no files/folders/routes renamed or
moved; no tables dropped/recreated; dead files (`routers/admin.py`,
`treatment_courses.*`) left in place — flagged in AUDIT_REPORT under
"Structural Changes Required" pending your confirmation.
