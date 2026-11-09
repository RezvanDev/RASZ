from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import settings

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # If ADMIN_IDS is empty, allow all (or allow during local testing)
        if not settings.ADMIN_IDS:
            return await handler(event, data)

        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id and user_id not in settings.ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("🔒 <b>Доступ ограничен</b>\nЭтот бот является персональным финансовым помощником. Доступ разрешен только владельцу.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ ограничен.", show_alert=True)
            return

        return await handler(event, data)

