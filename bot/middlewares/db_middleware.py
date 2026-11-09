from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.database.db import AsyncSessionFactory
from bot.services.finance_service import FinanceService

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionFactory() as session:
            finance_service = FinanceService(session)

            # Auto-register user if incoming event has user info
            from_user = None
            if isinstance(event, Message) and event.from_user:
                from_user = event.from_user
            elif isinstance(event, CallbackQuery) and event.from_user:
                from_user = event.from_user

            if from_user:
                await finance_service.get_or_create_user(
                    telegram_id=from_user.id,
                    username=from_user.username,
                    full_name=from_user.full_name
                )

            data["session"] = session
            data["finance"] = finance_service
            return await handler(event, data)

