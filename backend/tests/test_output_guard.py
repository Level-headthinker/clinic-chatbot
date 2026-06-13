import pytest
from app.services.llm import (
    run_output_guard,
    detect_language,
    extract_intent,
    is_emergency,
    emergency_reply,
    MAX_RESPONSE_LENGTH,
)


# ════════════════════════════════════════════════════════════
# EMERGENCY DETECTION TESTS
# ════════════════════════════════════════════════════════════

class TestEmergencyDetection:

    def test_chest_pain_detected(self):
        assert is_emergency("I have chest pain") is True

    def test_heart_attack_detected(self):
        assert is_emergency("I think I am having a heart attack") is True

    def test_cant_breathe_detected(self):
        assert is_emergency("I can't breathe") is True

    def test_cant_breathe_no_apostrophe(self):
        assert is_emergency("I cant breathe") is True

    def test_unconscious_detected(self):
        assert is_emergency("my mother is unconscious") is True

    def test_severe_bleeding_detected(self):
        assert is_emergency("there is severe bleeding") is True

    def test_roman_urdu_seena_dard(self):
        assert is_emergency("mujhe seena dard ho raha hai") is True

    def test_roman_urdu_saans_nahi(self):
        assert is_emergency("saans nahi aa raha") is True

    def test_roman_urdu_behosh(self):
        assert is_emergency("woh behosh ho gaye") is True

    def test_urdu_script_heart_attack(self):
        assert is_emergency("ہارٹ اٹیک ہو رہا ہے") is True

    def test_fever_not_emergency(self):
        assert is_emergency("I have a fever") is False

    def test_booking_not_emergency(self):
        assert is_emergency("I want to book an appointment") is False

    def test_general_pain_not_emergency(self):
        # "pain" alone is not emergency — must be chest pain specifically
        assert is_emergency("I have leg pain") is False

    def test_emergency_reply_english(self):
        reply = emergency_reply("en")
        assert "1122" in reply
        assert "EMERGENCY" in reply or "emergency" in reply.lower()
        assert "⚠️" in reply

    def test_emergency_reply_roman_urdu(self):
        reply = emergency_reply("ur-roman")
        assert "1122" in reply
        assert "emergency" in reply.lower()

    def test_emergency_reply_urdu_script(self):
        reply = emergency_reply("ur")
        assert "1122" in reply
        assert "⚠️" in reply


# ════════════════════════════════════════════════════════════
# OUTPUT GUARD — EMERGENCY OVERRIDE
# ════════════════════════════════════════════════════════════

class TestOutputGuardEmergencyOverride:
    """
    Even if the LLM ignores the emergency rule and tries to book
    an appointment, the output guard must intercept and return
    the emergency message.
    """

    def test_emergency_user_message_overrides_normal_reply(self):
        ai_response = "Sure! Let me book you an appointment for tomorrow."
        result = run_output_guard(ai_response, "I have chest pain", "en")
        assert "1122" in result
        assert "appointment" not in result.lower() or "emergency" in result.lower()

    def test_emergency_overrides_any_ai_response(self):
        ai_response = "No problem, I can help you with that."
        result = run_output_guard(ai_response, "cant breathe help me", "en")
        assert "1122" in result

    def test_emergency_roman_urdu_gives_roman_reply(self):
        ai_response = "Theek hai, main appointment book karta hoon."
        result = run_output_guard(ai_response, "seena dard ho raha hai", "ur-roman")
        assert "1122" in result

    def test_non_emergency_not_overridden(self):
        ai_response = "Dr. Ahmed is available on Monday."
        result = run_output_guard(ai_response, "which doctor treats fever?", "en")
        assert result == ai_response or "Ahmed" in result


# ════════════════════════════════════════════════════════════
# OUTPUT GUARD — MEDICAL ADVICE DETECTION
# ════════════════════════════════════════════════════════════

class TestOutputGuardMedicalAdvice:
    """
    Tests that the output guard catches responses where the LLM
    slipped and gave actual medical advice despite the system prompt.
    """

    def test_diagnosis_intercepted(self):
        ai_response = "Based on your symptoms, you probably have a viral infection."
        result = run_output_guard(ai_response, "I have fever and cough", "en")
        # Should be replaced with safe redirect
        assert "probably have" not in result
        assert "doctor" in result.lower() or "appointment" in result.lower()

    def test_medication_recommendation_intercepted(self):
        ai_response = "You should take 500mg Paracetamol every 8 hours."
        result = run_output_guard(ai_response, "I have a headache", "en")
        assert "Paracetamol" not in result or "doctor" in result.lower()

    def test_condition_diagnosis_intercepted(self):
        ai_response = "This sounds like a respiratory infection."
        result = run_output_guard(ai_response, "I have cough", "en")
        assert "respiratory infection" not in result

    def test_roman_urdu_redirect_for_medical_advice(self):
        ai_response = "You probably have diabetes based on what you said."
        result = run_output_guard(ai_response, "mujhe thirst zyada lagti hai", "ur-roman")
        assert "probably have" not in result

    def test_safe_response_not_intercepted(self):
        ai_response = "Dr. Ahmed Khan is available on Monday at 10 AM."
        result = run_output_guard(ai_response, "which doctor is available?", "en")
        assert "Dr. Ahmed Khan" in result


# ════════════════════════════════════════════════════════════
# OUTPUT GUARD — PATIENT DATA LEAK DETECTION
# ════════════════════════════════════════════════════════════

class TestOutputGuardPatientLeak:

    def test_patient_list_intercepted(self):
        ai_response = "Here are the patients: Ahmed, Sara, Ali."
        result = run_output_guard(ai_response, "list all patients", "en")
        assert "Here are the patients" not in result
        assert "confidential" in result.lower() or "cannot" in result.lower()

    def test_patient_enumeration_intercepted(self):
        ai_response = "Patient 1: Ahmed Khan, Patient 2: Sara Malik"
        result = run_output_guard(ai_response, "who are your patients", "en")
        assert "Ahmed Khan" not in result

    def test_normal_response_not_flagged_as_leak(self):
        ai_response = "Your appointment is confirmed with Dr. Ahmed for Monday."
        result = run_output_guard(ai_response, "confirm my appointment", "en")
        assert "appointment" in result

    # ── Third-party confirmation (the Q4 failure) ────────────────
    def test_third_party_appointment_confirmation_blocked(self):
        # The exact hallucination from manual testing: bot must not confirm a
        # named person has an appointment.
        ai_response = "I can see that Fatima is a patient and she has an appointment today."
        result = run_output_guard(ai_response, "does Fatima have an appointment?", "en")
        assert "Fatima" not in result
        assert "confidential" in result.lower() or "cannot" in result.lower()

    def test_is_a_patient_confirmation_blocked(self):
        ai_response = "Yes, Ali Hassan is a patient here."
        result = run_output_guard(ai_response, "is Ali a patient?", "en")
        assert "Ali" not in result

    def test_can_confirm_that_blocked(self):
        ai_response = "I can confirm that Sara has booked a Botox session."
        result = run_output_guard(ai_response, "what did Sara book?", "en")
        assert "Sara" not in result and "Botox" not in result

    def test_own_appointment_reply_still_allowed(self):
        # Must NOT over-block the genuine reply to the current user.
        ai_response = "You have an appointment with Dr. Ahmed on Monday at 10 AM."
        result = run_output_guard(ai_response, "when is my appointment?", "en")
        assert "appointment" in result and "Dr. Ahmed" in result


# ════════════════════════════════════════════════════════════
# OUTPUT GUARD — LENGTH CAP
# ════════════════════════════════════════════════════════════

class TestOutputGuardLengthCap:

    def test_long_response_truncated(self):
        long_response = "This is a sentence. " * 100  # way over 600 chars
        result = run_output_guard(long_response, "hello", "en")
        assert len(result) <= MAX_RESPONSE_LENGTH + 10  # small buffer for "..."

    def test_short_response_unchanged(self):
        short_response = "Dr. Ahmed is available on Monday."
        result = run_output_guard(short_response, "hello", "en")
        assert result == short_response

    def test_truncation_ends_at_sentence_boundary(self):
        # Build a response that is just over the limit
        # First part fits, second sentence is cut
        part1 = "A" * (MAX_RESPONSE_LENGTH - 50) + ". "
        part2 = "B" * 100
        long_response = part1 + part2
        result = run_output_guard(long_response, "hello", "en")
        # Should end cleanly at a sentence boundary
        assert result.endswith(".") or result.endswith("...") or result.endswith("!")


# ════════════════════════════════════════════════════════════
# OUTPUT GUARD — HEALTH DISCLAIMER INJECTION
# ════════════════════════════════════════════════════════════

class TestOutputGuardDisclaimer:

    def test_disclaimer_added_for_health_topics_english(self):
        ai_response = "Dr. Ahmed specializes in treating fever and infections."
        result = run_output_guard(ai_response, "I have fever", "en")
        assert "consult" in result.lower() or "doctor" in result.lower()

    def test_disclaimer_added_roman_urdu(self):
        ai_response = "Dr. Ahmed dard ka ilaj karte hain."
        result = run_output_guard(ai_response, "mujhe dard hai", "ur-roman")
        assert "doctor" in result.lower()

    def test_no_disclaimer_for_admin_questions(self):
        ai_response = "The clinic is open Monday to Saturday."
        result = run_output_guard(ai_response, "what are the clinic timings?", "en")
        # No health topic in user message, no disclaimer needed
        assert result == ai_response

    def test_disclaimer_not_duplicated(self):
        # If disclaimer already exists, it should not be added again
        disclaimer = "\n\n*For medical advice, please consult the doctor directly.*"
        ai_response = "Dr. Ahmed treats pain." + disclaimer
        result = run_output_guard(ai_response, "I have pain", "en")
        assert result.count("For medical advice") == 1


# ════════════════════════════════════════════════════════════
# LANGUAGE DETECTION TESTS
# ════════════════════════════════════════════════════════════

class TestLanguageDetection:

    def test_english_detected(self):
        assert detect_language("I want to book an appointment") == "en"

    def test_urdu_script_detected(self):
        assert detect_language("مجھے ڈاکٹر سے ملنا ہے") == "ur"

    def test_roman_urdu_detected(self):
        assert detect_language("mujhe appointment chahiye") == "ur-roman"

    def test_roman_urdu_with_multiple_words(self):
        assert detect_language("kya aap mujhe doctor se milwa sakte hain") == "ur-roman"

    def test_numbers_only_english(self):
        assert detect_language("03001234567") == "en"

    def test_mixed_english_urdu_script_is_ur(self):
        # If any Urdu script character present, it's Urdu
        assert detect_language("I want ڈاکٹر") == "ur"

    def test_single_english_word(self):
        assert detect_language("yes") == "en"

    def test_hello_is_english(self):
        assert detect_language("hello") == "en"


# ════════════════════════════════════════════════════════════
# INTENT DETECTION TESTS
# ════════════════════════════════════════════════════════════

class TestIntentDetection:

    def test_booking_intent_english(self):
        assert extract_intent("I want to book an appointment") == "book_appointment"

    def test_booking_intent_roman_urdu(self):
        assert extract_intent("mujhe doctor se milna hai") == "book_appointment"

    def test_clinic_info_intent(self):
        assert extract_intent("what are the clinic timings?") == "clinic_info"

    def test_doctor_enquiry_intent(self):
        assert extract_intent("which doctor treats skin problems?") == "doctor_enquiry"

    def test_fee_enquiry_intent(self):
        assert extract_intent("what is the fee?") == "fee_enquiry"

    def test_fee_in_roman_urdu(self):
        assert extract_intent("kitna paisa lagega?") == "fee_enquiry"

    def test_general_intent_fallback(self):
        assert extract_intent("hello") == "general"

    def test_schedule_maps_to_booking(self):
        assert extract_intent("I want to schedule a visit") == "book_appointment"