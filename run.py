import asyncio
import logging
import sys
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN, DB_CONFIG
from src.handlers import router
from src.middlewares import RegisterMiddleware, DatabaseMiddleware
from db import init_db


# Основная функция для запуска бота
async def main() -> None:
    dp = Dispatcher()
    pool = await asyncpg.create_pool(**DB_CONFIG)

    # Инициализация базы данных
    await init_db(pool)

    # Подключение middlewares и роутеров
    dp.callback_query.middleware(DatabaseMiddleware(pool))
    dp.message.middleware(DatabaseMiddleware(pool))
    dp.message.middleware(RegisterMiddleware(pool))
    dp.include_router(router)

    # Создание и запуск бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    await dp.start_polling(bot)


# Запуск бота
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
