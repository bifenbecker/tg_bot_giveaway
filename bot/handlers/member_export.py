import typing
import asyncio

import aiofiles
from aiogram.dispatcher import FSMContext
from aiogram.utils.emoji import emojize, demojize
from aiogram import types, md
from tortoise import exceptions as tortoise_exc, functions as tfunc
from tortoise.query_utils import Prefetch
from aiogram.utils import exceptions as aiogram_exc
from loguru import logger

from bot.misc import dp, bot
from bot import config, keyboards as kb
from bot import models
from bot import states as st
from bot import utils
from bot.models import giveaway
from ._helpers import *


@dp.callback_query_handler(kb.cbk.export.filter(action='prepare'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True)
async def export_index(query: types.CallbackQuery,
                       callback_data: typing.Dict[str, str],
                       state: FSMContext):
    logger.info("Admin [{user_id}] in export index page", user_id=query.from_user.id)
    
    giveaway_id = int(callback_data['value'])

    await st.GiveAwayExportState.type.set()

    async with state.proxy() as data:
        data['giveaway_id'] = giveaway_id

    await query.answer("")
    await asyncio.sleep(0.05)
    await query.message.edit_text("Выберите ниже что хотите скачать: ",
                                  reply_markup=kb.giveaway_members_export())

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.export.filter(action='nav', value='back'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayExportState.type)
async def export_back_to_giveaway(query: types.CallbackQuery,
                                  callback_data: typing.Dict[str, str],
                                  state: FSMContext):

    logger.info('Admin [{user_id}] back to GiveAway index page', user_id=query.from_user.id)

    await query.answer("")
    data = await state.get_data()
    giveaway = await models.GiveAway.filter(pk=int(data['giveaway_id']))\
        .prefetch_related(Prefetch("posts_templates",
                                   queryset=models.GiveAwayPostTemplate.all().limit(1)),
                          "sponsors", "published_posts",
                          "author").first()
    await state.finish()

    author = get_author_name(giveaway.author)
    posts_count = len(giveaway.published_posts)
    members_count = await models.GiveAwayMember.filter(giveaway_id=giveaway.id).count()
    giveaway_text = page_giveaway_in(author,
                                     giveaway.id,
                                     giveaway.name,
                                     sponsors_count=len(giveaway.sponsors),
                                     templates=1 if giveaway.posts_templates else 0,
                                     published_posts_count=posts_count, 
                                     status=giveaway.active, 
                                     members_count=members_count)

    post_url = temp[0].url if (temp := giveaway.posts_templates) else None

    await query.message.edit_text(giveaway_text,
                                  reply_markup=kb.giveaway_with_post_kb(
                                      giveaway.id, post_url=post_url, 
                                      done=not giveaway.active))

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.export.filter(action='download', value='members_txt'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayExportState.type)
async def export_members_txt(query: types.CallbackQuery,
                             callback_data: typing.Dict[str, str],
                             state: FSMContext):
    await query.answer("Запрос обрабатывается...")

    data = await state.get_data()
    giveaway_id = int(data['giveaway_id'])

    logger.info(f"Export giveaway id[{giveaway_id}] members. Txt file... ")

    members_data = await models.GiveAwayMember.filter(
        giveaway_id=giveaway_id).prefetch_related('user')\
        .values_list('user__first_name',
                     'user__last_name', 'user__username', 'user__id')

    filename = config.WINNERS_TXT_DIR / f'giveaway_{giveaway_id}_members.txt'

    try:
        async with aiofiles.open(filename, 'w',encoding='utf8') as f:
            await f.write('pid,firstname,lastname,username,userid\n')
            for index, member in enumerate(members_data):
                await f.write(f"{index+1}," + ",".join([
                    str(x) if x else "" for x in member]
                ) + "\n")

    except Exception as e:
        logger.error("Export txt error: {error}", error=e)
        return await query.answer('Невозможно экспортировать файл.')
    finally:
        del members_data
        
    await types.ChatActions.upload_document()
    await query.message.answer_document(types.InputFile(filename))
