import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
import asyncpg


class RegisterMiddleware(BaseMiddleware):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        try:
            async with self.pool.acquire() as conn:
                tg_id = event.from_user.id
                full_name = event.from_user.full_name
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1", tg_id
                )
                if not user:
                    await conn.execute(
                        "INSERT INTO users (user_id, full_name) VALUES ($1, $2)",
                        tg_id,
                        full_name,
                    )

            return await handler(event, data)
        except Exception as e:
            logging.error(f"Error in RegisterMiddleware: {e}")
            return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, pool):
        self.pool = pool

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        data["db_pool"] = self.pool
        return await handler(event, data)
