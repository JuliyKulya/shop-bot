import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import create_tables
from handlers import router
from additional_handlers import additional_router
from products_handlers import products_router
from saved_data_handlers import saved_data_router
from access_middleware import AccessMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main bot initialization and startup function."""
    create_tables()

    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    dp.include_router(additional_router)
    dp.include_router(products_router)
    dp.include_router(saved_data_router)
    dp.include_router(router)

    try:
        print("🤖 Bot started!")
        if config.ALLOWED_USERS:
            print(f"🔒 Access allowed for users: {config.ALLOWED_USERS}")
        else:
            print("🌍 Access open for all users")

        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
