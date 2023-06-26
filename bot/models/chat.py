from tortoise import fields
from .db import BaseModel, TimedBaseModel
from aiogram.types import Chat


class TelegramChat(TimedBaseModel):
    id = fields.BigIntField(pk=True)
    type = fields.CharField(50)
    title = fields.CharField(128, null=True)
    username = fields.CharField(100, null=True)
    first_name = fields.CharField(100, null=True)
    last_name = fields.CharField(100, null=True)
    bio = fields.TextField(null=True)
    description = fields.TextField(null=True)
    invite_link = fields.CharField(200, null=True)