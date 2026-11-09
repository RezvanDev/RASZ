import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import settings
from bot.database.db import AsyncSessionFactory
from bot.services.finance_service import FinanceService

logger = logging.getLogger(__name__)

async def daily_interest_job(bot: Bot):
    """
    Automatically calculates and accrues daily interest for all bank deposits/investments.
    Sends notifications to users about their passive income.
    """
    logger.info("Running daily interest calculation job...")
    async with AsyncSessionFactory() as session:
        finance = FinanceService(session)
        accruals = await finance.process_daily_deposit_yields(target_date=date.today())

        if not accruals:
            logger.info("No active deposits or interest accrued today.")
            return

        # Group accruals by user
        user_accruals = {}
        for acc in accruals:
            u_id = acc["user_id"]
            user_accruals.setdefault(u_id, []).append(acc)

        for u_id, items in user_accruals.items():
            total_earned = sum(i["amount"] for i in items)
            lines = [f"• <b>{i['account_name']}:</b> +{i['amount']:,.0f} сум (Баланс: {i['new_balance']:,.0f} сум)" for i in items]

            message_text = (
                "🌅 <b>Утренний отчет по пассивному доходу:</b>\n\n"
                f"Сегодня ваши активы заработали: <b>+{total_earned:,.0f} сум</b>\n\n"
                + "\n".join(lines) +
                "\n\nДеньги продолжают работать на вас! 🚀"
            )

            try:
                # Find telegram_id for user
                from bot.database.models import User
                user_obj = await session.get(User, u_id)
                if user_obj and user_obj.daily_reminders:
                    await bot.send_message(user_obj.telegram_id, message_text)
            except Exception as e:
                logger.error(f"Failed to send daily passive income notification to user {u_id}: {e}")

async def weekly_database_backup_job(bot: Bot):
    """Sends SQLite database backup to all admins every Sunday."""
    from pathlib import Path
    from aiogram.types import FSInputFile

    db_file = Path("data/finance.db")
    if not db_file.exists():
        return

    admin_ids = settings.ADMIN_IDS if isinstance(settings.ADMIN_IDS, list) else []
    for admin_id in admin_ids:
        try:
            doc = FSInputFile(str(db_file), filename=f"finance_backup_{date.today()}.db")
            await bot.send_document(
                chat_id=admin_id,
                document=doc,
                caption=f"📦 <b>Еженедельный автоматический бэкап базы данных</b> ({date.today().strftime('%d.%m.%Y')})"
            )
        except Exception as e:
            logger.error(f"Failed to send backup to admin {admin_id}: {e}")

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    # Run daily interest accrual at 00:05 midnight every day
    scheduler.add_job(
        daily_interest_job,
        trigger="cron",
        hour=0,
        minute=5,
        kwargs={"bot": bot},
        id="daily_interest_job",
        replace_existing=True
    )

    # Run weekly backup on Sunday at 03:00 AM
    scheduler.add_job(
        weekly_database_backup_job,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        kwargs={"bot": bot},
        id="weekly_backup_job",
        replace_existing=True
    )

    return scheduler

