from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),       # Gmail App Password
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME="StudentHub by Edhub360",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

# Dynamic URL based on environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_URL = (
    "https://app.edhub360.com"
    if ENVIRONMENT == "production"
    else "https://edhub360.github.io/StudentHub"
)


async def send_subscription_success_email(
    to_email: str,
    user_name: str,
    plan_name: str,
    amount: float,
    currency: str,
    expires_at: datetime,
):
    # Free plan — don't show amount
    amount_row = (
        f"<li><b>Amount Paid:</b> Free</li>"
        if amount == 0
        else f"<li><b>Amount Paid:</b> {currency.upper()} {amount:.2f}</li>"
    )

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #2563eb;">🎉 Subscription Activated – StudentHub</h2>
        <p>Hi <strong>{user_name}</strong>,</p>
        <p>Your <strong>{plan_name}</strong> plan is now active. You have full access to StudentHub features.</p>
        <ul>
            {amount_row}
            <li><b>Plan Expires On:</b> {expires_at.strftime('%B %d, %Y')}</li>
        </ul>
        <p>Happy learning! 🚀</p>
        <a href="{APP_URL}" 
           style="display:inline-block;background:#2563eb;color:white;padding:10px 24px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin-top:12px;">
            Go to Dashboard
        </a>
        <br><br>
        <p style="color:#6b7280;font-size:13px;">– The Edhub360 Team</p>
    </div>
    """

    message = MessageSchema(
        subject=f" {plan_name} Plan Active – StudentHub",
        recipients=[to_email],
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def send_subscription_expiry_email(
    to_email: str,
    user_name: str,
    plan_name: str,
    expires_at: datetime,
    days_remaining: int,
):
    if days_remaining > 0:
        subject = f"⚠️ Your StudentHub Subscription Expires in {days_remaining} Day(s)"
        headline = f"Your <strong>{plan_name}</strong> plan expires in <strong>{days_remaining} day(s)</strong>."
        cta = "Renew now to avoid any interruption to your learning."
    else:
        subject = "❌ Your StudentHub Subscription Has Expired"
        headline = f"Your <strong>{plan_name}</strong> plan has <strong>expired</strong>."
        cta = "Resubscribe to regain access to all premium features."

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #dc2626;">StudentHub Subscription Notice</h2>
        <p>Hi <strong>{user_name}</strong>,</p>
        <p>{headline}</p>
        <ul>
            <li><b>Plan:</b> {plan_name}</li>
            <li><b>Expiry Date:</b> {expires_at.strftime('%B %d, %Y')}</li>
        </ul>
        <p>{cta}</p>
        <a href="{APP_URL}/subscription"
           style="display:inline-block;background:#2563eb;color:white;padding:10px 24px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin-top:12px;">
            Manage Subscription
        </a>
        <br><br>
        <p style="color:#6b7280;font-size:13px;">– The Edhub360 Team</p>
    </div>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
