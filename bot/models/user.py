from tortoise import fields
from .db import BaseModel, TimedBaseModel
from aiogram.types import User


class TelegramUser(TimedBaseModel):

    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=32, null=True, unique=True)
    is_bot = fields.BooleanField(default=False)
    first_name = fields.CharField(max_length=64, null=True)
    last_name = fields.CharField(max_length=64, null=True)
    language_code = fields.CharField(max_length=10)
    
