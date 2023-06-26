import asyncio
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import CommandHelp, CommandStart, Command, Text
from aiogram.types import chat_invite_link
from aiogram.utils.emoji import emojize, demojize
from aiogram import types, md
from aiogram.utils import exceptions as aiogram_exc
from aiogram.utils.mixins import T

from bot.keyboards import btn
from bot.misc import dp, bot
from bot import config, keyboards as kb, states as st
from bot import models


# @dp.channel_post_handler(lambda m: m.chat.id == config.POST_TEMPLATES_CHANNEL_ID)
# async def channel_message(message: types.Message):
#     print("POST: ", message)
# # ---------------------------------------------------------------------------------


# @dp.edited_channel_post_handler(lambda m: m.chat.id == config.POST_TEMPLATES_CHANNEL_ID)
# async def channel_message(message: types.Message):
#     print("EDIT: ", message)