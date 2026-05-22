CREATE UNIQUE INDEX IF NOT EXISTS uq_active_appointment_slot
ON appointments (tenant_id, doctor_id, slot_datetime)
WHERE status IN ('pending', 'confirmed');
