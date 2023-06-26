from collections import Counter
import os
import asyncio
import typing
import random
import aiofiles
from contextlib import suppress
from aiogram.dispatcher import FSMContext
from aiogram.utils.emoji import emojize, demojize
from aiogram import types, md
from aiogram.utils.markdown import pre
from pypika.queries import Join
from tortoise import exceptions as tortoise_exc, functions as tfunc
from tortoise.query_utils import Q, Prefetch
from aiogram.utils import exceptions as aiogram_exc
from loguru import logger
from bot.keyboards.main import cancel_kb

from bot.misc import dp, bot
from bot import config, keyboards as kb
from bot import models
from bot import states as st
from bot import utils
from bot.models import giveaway
from ._helpers import *


@dp.message_handler(commands={'logreport'},
                    chat_type=[types.ChatType.PRIVATE],
                    is_admin=True)
async def cmd_log_report(message: types.Message):
    """
    /logreport - Команда для получения логов
    - /logreport - получаем два последних лога
    - /logreport 3 - получаем последние 3 лога
    - /logreport 2 3 - пропускаем первые два файлы и получаем следующие три
    """
    args = []

    with suppress(ValueError):
        args = [int(x) for x in a.split(',' if ',' in a else ' ')] if (
            a := message.get_args()) else []

    offset, count = a if len(
        a := (args if args else (0, 2))) == 2 else (0, a[0])

    files_count = 0

    def get_logs() -> typing.Union[str, None]:
        nonlocal files_count
        files = sorted(config.LOG_DIR.iterdir(),
                       key=os.path.getmtime,
                       reverse=True)
        files_count = len(files)
        if offset >= len(files):
            yield None
        for fname in files[offset:]:
            yield str(fname)
        yield None

    logs = get_logs()

    while (log_file := next(logs)) and count > 0:
        await asyncio.sleep(0.3)
        await types.ChatActions.upload_document()
        await message.reply_document(types.InputFile(log_file))
        count -= 1

    del logs
