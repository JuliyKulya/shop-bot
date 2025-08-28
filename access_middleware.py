from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import config

class AccessMiddleware(BaseMiddleware):
    """Middleware to restrict bot access to allowed users only."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

        if user_id and user_id in config.ALLOWED_USERS:
            return await handler(event, data)
        else:
            if isinstance(event, Message):
                await event.answer("❌ You don't have access to this bot.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ You don't have access to this bot.", show_alert=True)
            return
