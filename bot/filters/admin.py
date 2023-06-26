from dataclasses import dataclass

from aiogram import types
from aiogram.dispatcher.filters.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data

from bot import config


@dataclass
class isAdmin(BoundFilter):
    key = "is_admin"
    is_admin: bool

    async def check(self, message: types.Message) -> bool:
        return message.from_user.id in config.ADMIN_IDS
