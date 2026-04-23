from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, text
from datetime import datetime, timezone
from db import AsyncSessionLocal
from models import Subscription
from email_service import send_subscription_expiry_email
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_expired_subscriptions():
    """
    Runs daily at 02:00 UTC.
    Safety net for missed Stripe webhooks — the real-time API guard in
    get_current_subscription() handles the per-request race condition.
    """
    logger.info("🕐 Running daily subscription expiry check...")
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.current_period_end < now,
                    Subscription.cancel_at == None,
                )
            )
            expired_subs = result.scalars().all()

            if not expired_subs:
                logger.info("✅ No expired subscriptions found.")
                return

            logger.info(f"⚠️ Found {len(expired_subs)} expired subscription(s)")

            for sub in expired_subs:
                # 1. Mark subscription as expired
                await db.execute(
                    text("""
                        UPDATE stud_hub_schema.subscriptions
                        SET status = 'expired', ended_at = :now
                        WHERE id = :sub_id
                    """),
                    {"now": now, "sub_id": str(sub.id)},
                )

                # 2. Downgrade user tier → locks all premium features
                await db.execute(
                    text("""
                        UPDATE stud_hub_schema.users
                        SET subscription_tier = NULL
                        WHERE user_id = (
                            SELECT user_id FROM stud_hub_schema.customers
                            WHERE id = :customer_id
                        )
                    """),
                    {"customer_id": str(sub.customer_id)},
                )

                # 3. Send expiry email — isolated so one failure doesn't abort the batch
                try:
                    user_result = await db.execute(
                        text("""
                            SELECT u.email, u.name, p.name AS plan_name
                            FROM stud_hub_schema.users u
                            JOIN stud_hub_schema.customers c ON c.user_id = u.user_id
                            JOIN stud_hub_schema.subscriptions s ON s.customer_id = c.id
                            JOIN stud_hub_schema.plans p ON p.id = s.plan_id
                            WHERE c.id = :customer_id
                        """),
                        {"customer_id": str(sub.customer_id)},
                    )
                    user_row = user_result.fetchone()
                    if user_row:
                        await send_subscription_expiry_email(
                            to_email=user_row.email,
                            user_name=user_row.name or user_row.email,
                            plan_name=user_row.plan_name,
                            expires_at=sub.current_period_end,
                            days_remaining=0,
                        )
                        logger.info(f"📧 Expiry email sent to {user_row.email}")
                except Exception as e:
                    logger.error(f"❌ Email failed (non-blocking): {e}")

            await db.commit()
            logger.info(f"✅ Processed {len(expired_subs)} expired subscription(s)")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Scheduler error: {e}")


def start_scheduler():
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="check_expired_subscriptions",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("⏰ Scheduler started — daily expiry check at 02:00 UTC (07:30 IST)")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("⏰ Scheduler stopped")