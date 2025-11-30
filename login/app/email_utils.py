import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

def send_reset_password_email(to_email: str, reset_url: str) -> None:
    subject = "Reset your EdHub360 password"
    body = (
        f"Hi,\n\n"
        f"We received a request to reset your EdHub360 password.\n\n"
        f"Click the link below to choose a new password:\n{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"Thanks,\n"
        f"{settings.smtp_from_name}"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        logger.info(f"Password reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        # Do not raise; forgot-password endpoint should still return generic success
