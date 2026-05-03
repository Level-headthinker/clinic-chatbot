import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_email(to: str, subject: str, body: str):
    if not settings.MAIL_EMAIL or not settings.MAIL_PASSWORD:
        print("Email not configured — skipping")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.MAIL_EMAIL
        msg["To"] = to

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.MAIL_EMAIL, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_EMAIL, to, msg.as_string())

        print(f"Email sent to {to}")

    except Exception as e:
        print(f"Email failed: {e}")


def send_booking_notification(
    patient_name: str,
    patient_phone: str,
    patient_concern: str,
    doctor_name: str,
    slot: str,
    clinic_name: str
):
    subject = f"New Appointment Booked — {patient_name}"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
        <div style="max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">

            <div style="background: #1e3a5f; padding: 20px;">
                <h2 style="color: white; margin: 0;">🏥 New Appointment</h2>
                <p style="color: #93c5fd; margin: 4px 0 0 0;">{clinic_name}</p>
            </div>

            <div style="padding: 24px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b; width: 40%;">Patient Name</td>
                        <td style="padding: 10px 0; font-weight: bold;">{patient_name}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b;">Phone</td>
                        <td style="padding: 10px 0; font-weight: bold;">{patient_phone}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b;">Concern</td>
                        <td style="padding: 10px 0;">{patient_concern}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b;">Doctor</td>
                        <td style="padding: 10px 0; font-weight: bold;">Dr. {doctor_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #64748b;">Slot</td>
                        <td style="padding: 10px 0; font-weight: bold;">{slot}</td>
                    </tr>
                </table>

                <div style="margin-top: 20px; background: #eff6ff; padding: 14px; border-radius: 8px;">
                    <p style="margin: 0; color: #2563eb; font-size: 14px;">
                        ⚡ Login to your dashboard to confirm or reschedule this appointment.
                    </p>
                </div>
            </div>

            <div style="background: #f8fafc; padding: 14px; text-align: center;">
                <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                    Sent by ClinicBot AI — Automated notification
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(settings.ADMIN_EMAIL, subject, body)


def send_lead_notification(
    patient_name: str,
    patient_phone: str,
    concern: str,
    clinic_name: str
):
    subject = f"New Lead — {patient_name}"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
        <div style="max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">

            <div style="background: #0d9488; padding: 20px;">
                <h2 style="color: white; margin: 0;">👤 New Lead Captured</h2>
                <p style="color: #99f6e4; margin: 4px 0 0 0;">{clinic_name}</p>
            </div>

            <div style="padding: 24px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b; width: 40%;">Name</td>
                        <td style="padding: 10px 0; font-weight: bold;">{patient_name}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 10px 0; color: #64748b;">Phone</td>
                        <td style="padding: 10px 0; font-weight: bold;">{patient_phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #64748b;">Concern</td>
                        <td style="padding: 10px 0;">{concern}</td>
                    </tr>
                </table>

                <div style="margin-top: 20px; background: #f0fdf4; padding: 14px; border-radius: 8px;">
                    <p style="margin: 0; color: #16a34a; font-size: 14px;">
                        📞 Follow up with this patient as soon as possible.
                    </p>
                </div>
            </div>

            <div style="background: #f8fafc; padding: 14px; text-align: center;">
                <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                    Sent by ClinicBot AI — Automated notification
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(settings.ADMIN_EMAIL, subject, body)