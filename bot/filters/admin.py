from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject


class AdminFilter(BaseFilter):
    async def __call__(
        self, event: TelegramObject, config: Any, db: Any = None
    ) -> bool:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        if not user:
            return False
        if user.id == config.admin_id:
            return True
        if db:
            return await db.is_admin(user.id, config.admin_id)
        return False
