from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from datetime import datetime

conf = ConnectionConfig(
    MAIL_USERNAME="your@gmail.com",
    MAIL_PASSWORD="your-app-password",       # Use Gmail App Password
    MAIL_FROM="your@gmail.com",
    MAIL_FROM_NAME="Edhub360",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_subscription_success_email(
    to_email: str,
    user_name: str,
    plan_name: str,
    amount: float,
    currency: str,
    expires_at: datetime,
):
    body = f"""
    <h2>🎉 Subscription Activated – Edhub360</h2>
    <p>Hi <strong>{user_name}</strong>,</p>
    <p>Your payment was successful and your <strong>{plan_name}</strong> plan is now active.</p>
    <ul>
        <li><b>Amount Paid:</b> {currency.upper()} {amount:.2f}</li>
        <li><b>Plan Expires On:</b> {expires_at.strftime('%B %d, %Y')}</li>
    </ul>
    <p>You now have full access to all Edhub360 premium features. Happy learning! 🚀</p>
    <br>
    <p>– The Edhub360 Team</p>
    """
    message = MessageSchema(
        subject="✅ Payment Successful – Your Edhub360 Subscription is Active",
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
        subject = f"⚠️ Your Edhub360 Subscription Expires in {days_remaining} Day(s)"
        headline = f"Your subscription expires in <strong>{days_remaining} day(s)</strong>."
        cta = "Renew now to avoid interruption."
    else:
        subject = "❌ Your Edhub360 Subscription Has Expired"
        headline = "Your subscription has <strong>expired</strong>."
        cta = "Resubscribe to regain access to all premium features."

    body = f"""
    <h2>Edhub360 Subscription Notice</h2>
    <p>Hi <strong>{user_name}</strong>,</p>
    <p>{headline}</p>
    <ul>
        <li><b>Plan:</b> {plan_name}</li>
        <li><b>Expiry Date:</b> {expires_at.strftime('%B %d, %Y')}</li>
    </ul>
    <p>{cta}</p>
    <a href="https://edhub360.com/subscription" style="background:#2563eb;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;">
        Manage Subscription
    </a>
    <br><br>
    <p>– The Edhub360 Team</p>
    """
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
