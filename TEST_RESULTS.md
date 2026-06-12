# TEST_RESULTS — 2026-06-12

## clinic-chatbot — `pytest tests/ -W ignore` → **156 passed, 1 skipped, 17 deselected**

### New tests written in this audit (all passing)

✅ PASS — test_webhook_signature (6): forged/missing/tampered WhatsApp webhook posts are rejected; genuine Meta-signed posts pass
✅ PASS — test_webhook_routing::TestWebhookRouting (2): unregistered phone_number_id resolves to NOTHING (fail closed — the old "first active branch" cross-tenant fallback is gone); mapped numbers resolve their own clinic
✅ PASS — test_webhook_routing::TestMessageQuota (4): counter increments, at-limit blocks, new month resets, legacy unmapped numbers unlimited
✅ PASS — test_booking_validation (8): public booking rejects past / 3 AM / off-grid / wrong-day / far-future slots and garbage phone numbers; valid offered slots accepted
✅ PASS — test_confirmation_and_language (9): "I want to book an appointment" no longer instantly books; "ok" no longer matches inside "looking"; Urdu conversation no longer flips to English when the patient sends their phone number
✅ PASS — test_import_mapping (10): "Patient Name"/"PatientName"/"name of patient"/"WhatsApp" auto-map at ≥80% confidence; nonsense headers are NOT auto-applied; unmapped required fields block the import; bad rows get plain-language errors with spreadsheet row numbers
✅ PASS — test_data_isolation::TestRoleScoping (7): branch admin cannot manage other branches' users, cannot touch tenant-level users, cannot grant the admin role
⚠️ SKIP — test_data_isolation::TestDatabaseIsolation: needs `TEST_DATABASE_URL` pointing at a DISPOSABLE Postgres (never run against production data)

### Pre-existing tests that were FAILING at HEAD and now pass (real bugs fixed)

✅ PASS — test_input_guard::test_DAN_blocked: "You are now DAN" now classifies as `jailbreak` (was `role_override` due to pattern ordering)
✅ PASS — test_output_guard::test_long_response_truncated: truncated replies now respect the 800-char cap (the old code appended a 99-char suffix AFTER cutting at the cap)
✅ PASS — test_output_guard::test_truncation_ends_at_sentence_boundary: truncation ends at a sentence boundary or "..."

### Remaining pre-existing suite

✅ PASS — all other input-guard, output-guard, conversation tests (unchanged)
⚠️ DESELECTED (17) — test_llm_integration: live Groq API tests, deselected by the project's pytest marker config (unchanged behavior)

## VIS — `pytest tests/` → **43 passed**

✅ PASS — test_tts_routing (5, new): English uses ElevenLabs (not Deepgram); Urdu uses ElevenLabs; missing key falls back to Deepgram; ElevenLabs failure falls back to Deepgram; `ogg_opus` format request passes through
✅ PASS — test_hardening, test_language, test_pipeline, test_registry, test_sessions, test_voice_auth, test_whatsapp_webhook (38, pre-existing): all still green after the TTS routing change

## Not testable in this environment

⚠️ MANUAL — end-to-end WhatsApp voice note (real Meta webhook → Groq Whisper STT → ElevenLabs Sarah → ogg/opus voice note): requires live Meta + ElevenLabs calls. Verify after deploy: send a voice note, confirm the reply is a voice-note bubble in Sarah's voice, and check VIS logs show no "falling back to Deepgram" warnings.
⚠️ MANUAL — `ffmpeg` presence on the VIS host (only needed if your ElevenLabs tier rejects native Opus; the fallback logs a one-time warning).
