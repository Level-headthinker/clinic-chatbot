# WhatsApp message templates (for automatic reminders)

WhatsApp only lets you send **free-form** messages within **24 hours** of the
patient's last message. Reminders sent days later (next-visit reminders, lead
nudges, appointment reminders) fall outside that window and therefore require a
**pre-approved template message**.

Once you create and get these templates approved in Meta, set the matching env
vars and the reminder agent will use them automatically (it falls back to
free-form text when a template name is blank or when the patient is inside the
24h window).

## One-time setup in Meta

1. Go to **Meta Business Manager → WhatsApp Manager → Message templates → Create template**.
2. Category: **Utility** (reminders/transactional). Language: match `WA_TEMPLATE_LANG`.
3. Create the three templates below — the **body parameter order must match** what
   the app sends (`{{1}}`, `{{2}}`, …). You can change the wording freely; only the
   number and order of `{{n}}` placeholders must match.
4. After approval, set the env vars to each template's **name**.

## Templates

### 1. Next-visit reminder → `WA_TEMPLATE_NEXT_VISIT`
Parameters: `{{1}}` patient name · `{{2}}` clinic · `{{3}}` doctor · `{{4}}` date
> Hi {{1}}! A gentle reminder from {{2}}: your next visit with {{3}} is coming up
> on {{4}}. Reply here to confirm or reschedule — we look forward to seeing you.

### 2. Lead nudge → `WA_TEMPLATE_LEAD_NUDGE`
Parameters: `{{1}}` name · `{{2}}` clinic
> Hi {{1}}! This is {{2}}. You recently reached out to us and we'd love to help.
> Would you like to book an appointment or have any questions? Just reply here.

### 3. Appointment reminder (24h before) → `WA_TEMPLATE_APPT_REMINDER`
Parameters: `{{1}}` patient name · `{{2}}` clinic · `{{3}}` doctor · `{{4}}` date & time
> Hi {{1}}! A reminder from {{2}}: your appointment with {{3}} is on {{4}}.
> Please arrive 10 minutes early. Reply to reschedule.

## Env vars
```
WA_TEMPLATE_LANG=en              # the language code your templates were approved in
WA_TEMPLATE_NEXT_VISIT=next_visit_reminder
WA_TEMPLATE_LEAD_NUDGE=lead_nudge
WA_TEMPLATE_APPT_REMINDER=appointment_reminder
```

Leave any of these blank to skip templating for that reminder (it will then only
deliver to patients who messaged within the last 24 hours).
