import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from bot.database.db import init_db
from bot.middlewares.auth_middleware import AuthMiddleware
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.handlers import commands, callbacks, messages
from bot.scheduler import setup_scheduler
from aiogram.types import BotCommand

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    bot_commands = [
        BotCommand(command="dashboard", description="📱 Полный финансовый дашборд"),
        BotCommand(command="balance", description="💰 Баланс, активы и кредитки"),
        BotCommand(command="report", description="📊 Аналитика и отчет с графиком"),
        BotCommand(command="deposit", description="📈 Вклады и пассивный доход"),
        BotCommand(command="goals", description="🎯 Финансовые цели"),
        BotCommand(command="export", description="📄 Выгрузка в Excel (CSV)"),
        BotCommand(command="backup", description="📦 Бэкап базы данных"),
        BotCommand(command="help", description="ℹ️ Инструкция и возможности"),
    ]
    await bot.set_my_commands(bot_commands)

async def main():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in environment or .env file! Exiting...")
        sys.exit(1)

    logger.info("Initializing database...")
    await init_db()

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Set up Telegram menu commands button
    await setup_bot_commands(bot)

    # Register Middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # Register Handlers
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(messages.router)

    # Setup Background Scheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Background scheduler started (daily interest & notifications).")

    logger.info("Bot is starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated.")

