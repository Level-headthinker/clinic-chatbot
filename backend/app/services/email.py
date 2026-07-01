import logging
import smtplib
import threading
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str):
    if not settings.MAIL_EMAIL or not settings.MAIL_PASSWORD:
        logger.info("Email is not configured; skipping notification")
        return

    def _send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.MAIL_EMAIL
            msg["To"] = to
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                server.login(settings.MAIL_EMAIL, settings.MAIL_PASSWORD)
                server.sendmail(settings.MAIL_EMAIL, to, msg.as_string())

            logger.info("Email sent to %s", to)
        except Exception as e:
            logger.exception("Email failed: %s", e)

    threading.Thread(target=_send, daemon=True).start()


def send_password_reset_email(to: str, reset_link: str, clinic_name: str = "ClinicBot"):
    clinic_name = escape(clinic_name or "ClinicBot")
    reset_link_attr = escape(reset_link or "")
    body = f"""
    <html><body style="font-family: Arial, sans-serif; padding: 24px; color: #1e293b;">
      <div style="max-width: 480px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
        <div style="background: #0d9488; padding: 20px;">
          <h2 style="color: #fff; margin: 0;">Reset your password</h2>
        </div>
        <div style="padding: 24px;">
          <p>We received a request to reset your {clinic_name} password.</p>
          <p style="margin: 24px 0;">
            <a href="{reset_link_attr}" style="background:#0d9488;color:#fff;text-decoration:none;
               padding:12px 22px;border-radius:8px;display:inline-block;font-weight:bold;">
               Reset password</a>
          </p>
          <p style="font-size: 13px; color: #64748b;">
            This link expires in 30 minutes. If you didn't request this, you can safely ignore this email —
            your password won't change.
          </p>
          <p style="font-size: 12px; color: #94a3b8; word-break: break-all;">{reset_link_attr}</p>
        </div>
      </div>
    </body></html>
    """
    send_email(to, "Reset your password", body)


def send_welcome_email(to: str, clinic_name: str, admin_name: str = "", login_link: str = ""):
    """Sent right after a clinic signs up — warm welcome + next steps."""
    clinic_name = escape(clinic_name or "your clinic")
    first = escape((admin_name or "").split(" ")[0] if admin_name else "there")
    login_attr = escape(login_link or "")
    cta = (f'<a href="{login_attr}" style="background:#0d9488;color:#fff;text-decoration:none;'
           f'padding:12px 22px;border-radius:8px;display:inline-block;font-weight:bold;">'
           f'Log in &amp; finish setup</a>') if login_attr else ""
    body = f"""
    <html><body style="font-family: Arial, sans-serif; padding: 24px; color: #1e293b;">
      <div style="max-width: 520px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
        <div style="background: #0d9488; padding: 22px;">
          <h2 style="color:#fff; margin:0;">Welcome to ClinicBot 🎉</h2>
          <p style="color:#99f6e4; margin:4px 0 0;">{clinic_name}</p>
        </div>
        <div style="padding: 24px;">
          <p>Hi {first},</p>
          <p>Your clinic account is ready, and your <strong>3-day free trial</strong> has started.
             Here's how to get your AI assistant live in minutes:</p>
          <ol style="color:#334155; font-size:14px; line-height:1.9; padding-left:18px;">
            <li>Personalise your bot's welcome message &amp; tone</li>
            <li>Add your clinic details and working hours</li>
            <li>Add at least one doctor (so the bot can book)</li>
            <li>Connect your WhatsApp number and try it out</li>
          </ol>
          <p style="margin: 22px 0;">{cta}</p>
          <p style="font-size: 13px; color: #64748b;">
            The Getting Started guide on your dashboard walks you through each step.
            Reply to this email if you need a hand.
          </p>
        </div>
        <div style="background:#f8fafc; padding:14px; text-align:center;">
          <p style="margin:0; color:#94a3b8; font-size:12px;">ClinicBot — your clinic's AI assistant</p>
        </div>
      </div>
    </body></html>
    """
    send_email(to, f"Welcome to ClinicBot, {clinic_name}!", body)


def send_subscription_receipt_email(to: str, clinic_name: str, plan_label: str,
                                    price: str = "", next_billing: str = ""):
    """Sent when a subscription payment is confirmed (via the verified webhook)."""
    clinic_name = escape(clinic_name or "your clinic")
    plan_label = escape(plan_label or "")
    price = escape(str(price) if price else "")
    next_billing = escape(next_billing or "")
    rows = [("Clinic", clinic_name), ("Plan", plan_label)]
    if price:
        rows.append(("Amount", price))
    if next_billing:
        rows.append(("Next billing date", next_billing))
    tr = "".join(
        f'<tr style="border-bottom:1px solid #f1f5f9;">'
        f'<td style="padding:10px 0;color:#64748b;width:45%;">{k}</td>'
        f'<td style="padding:10px 0;font-weight:bold;">{v}</td></tr>'
        for k, v in rows
    )
    body = f"""
    <html><body style="font-family: Arial, sans-serif; padding: 24px; color: #1e293b;">
      <div style="max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
        <div style="background: #0d9488; padding: 22px;">
          <h2 style="color:#fff; margin:0;">Payment received ✅</h2>
          <p style="color:#99f6e4; margin:4px 0 0;">Thank you for subscribing</p>
        </div>
        <div style="padding: 24px;">
          <p>Your subscription is now active. Here are the details:</p>
          <table style="width:100%; border-collapse:collapse;">{tr}</table>
          <div style="margin-top:20px; background:#f0fdf4; padding:14px; border-radius:8px;">
            <p style="margin:0; color:#16a34a; font-size:14px;">
              Your plan is active — all features are unlocked. You can manage or cancel anytime
              from your dashboard's Subscription page.
            </p>
          </div>
        </div>
        <div style="background:#f8fafc; padding:14px; text-align:center;">
          <p style="margin:0; color:#94a3b8; font-size:12px;">ClinicBot — automated receipt</p>
        </div>
      </div>
    </body></html>
    """
    send_email(to, f"Your ClinicBot receipt — {plan_label}", body)


def send_booking_notification(
    patient_name: str,
    patient_phone: str,
    patient_concern: str,
    doctor_name: str,
    slot: str,
    clinic_name: str,
    to_email: str = "",
):
    patient_name = escape(patient_name or "")
    patient_phone = escape(patient_phone or "")
    patient_concern = escape(patient_concern or "")
    doctor_name = escape(doctor_name or "")
    slot = escape(slot or "")
    clinic_name = escape(clinic_name or "")
    subject = f"New Appointment Booked - {patient_name}"

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

    send_email(to_email or settings.ADMIN_EMAIL, subject, body)


def send_lead_notification(
    patient_name: str,
    patient_phone: str,
    concern: str,
    clinic_name: str,
    to_email: str = "",
):
    patient_name = escape(patient_name or "")
    patient_phone = escape(patient_phone or "")
    concern = escape(concern or "")
    clinic_name = escape(clinic_name or "")
    subject = f"New Lead - {patient_name}"

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

    send_email(to_email or settings.ADMIN_EMAIL, subject, body)
