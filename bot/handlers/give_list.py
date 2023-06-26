import typing
import asyncio
import aiogram

from aiogram.dispatcher import FSMContext, filters
from aiogram.utils.emoji import emojize, demojize
from aiogram import types, md
from tortoise import exceptions as tortoise_exc, functions as tfunc
from tortoise.query_utils import Prefetch
from aiogram.utils import exceptions as aiogram_exc
from loguru import logger
from aiogram.utils.deep_linking import get_start_link

from bot.misc import dp, bot
from bot import config, keyboards as kb
from bot.keyboards import btn
from bot import models
from bot import states as st
from bot import utils
from ._helpers import *


GIVE_IN_PAGE = 10


@dp.message_handler(lambda m: m.text == btn.text_all_giveaways,
                    is_admin=True,
                    chat_type=[types.ChatType.PRIVATE],)
async def giveaway_list(message: types.Message, state: FSMContext):

    giveaways = await models.GiveAway.all().order_by('-created_at').values('id', 'name')
    give_list = ["Чтобы перейти к ГИВу просто нажмите на него: "]

    page = 0
    count = 0

    for give in giveaways:
        give_list.append(f"/g{give['id']}" + " - " + give['name'])
        count += 1
        if count >= GIVE_IN_PAGE:
            break

    await message.answer("\n\n".join(give_list), reply_markup=kb.giveaway_list_nav_kb(page))

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.nav.filter(action='givelist'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True)
async def giveaway_pagination(query: types.CallbackQuery,
                              callback_data: typing.Dict[str, str],
                              state: FSMContext):
    give_list = ["Чтобы перейти к ГИВу просто нажмите на него: "]
    next_page = int(callback_data['value'])
    offset = (GIVE_IN_PAGE-1) * next_page
    if offset < 0:
        return await query.answer('Там ничего нет =)')
    giveaways = await models.GiveAway.all().order_by('-created_at').offset(offset).values('id', 'name')
    count = 0
    if not giveaways:
        return await query.answer(f"Это конец! =)")
    for give in giveaways:
        give_list.append(f"/g{give['id']}" + " - " + give['name'])
        count += 1
        if count >= GIVE_IN_PAGE:
            break
    await query.answer(f"Вы перешли на страницу: {next_page+1}")
    await query.message.edit_text("\n\n".join(give_list), reply_markup=kb.giveaway_list_nav_kb(next_page))

# ---------------------------------------------------------------------------------


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=['/g([0-9]*)']),
                    is_admin=True,
                    chat_type=[types.ChatType.PRIVATE],)
async def giveaway_item(message: types.Message, state: FSMContext, regexp_command):

    logger.info('Admin [{user_id}] back to GiveAway index page',
                user_id=message.from_user.id)

    giveaway_id = regexp_command.group(1)
    if not giveaway_id:
        return await message.answer('Нет такого гива!')

    giveaway = await models.GiveAway.filter(pk=giveaway_id)\
        .prefetch_related(Prefetch("posts_templates",
                                   queryset=models.GiveAwayPostTemplate.all().limit(1)),
                          "sponsors", "published_posts",
                          "author").first()
    # await state.finish()

    posts_count = len(giveaway.published_posts)
    author = get_author_name(giveaway.author)
    members_count = await models.GiveAwayMember.filter(giveaway_id=giveaway_id).count()

    winners = await models.GiveAwayWinner.filter(giveaway_id=giveaway_id).all()
    usernames = [f"@{x.username}" for x in winners]

    giveaway_text = page_giveaway_in(author,
                                     giveaway.id,
                                     giveaway.name,
                                     sponsors_count=len(giveaway.sponsors),
                                     templates=1 if giveaway.posts_templates else 0,
                                     published_posts_count=posts_count,
                                     status=giveaway.active,
                                     members_count=members_count, winner=', '.join(usernames))

    post_url = temp[0].url if (temp := giveaway.posts_templates) else None
    if post_url:
        keyboard = kb.giveaway_with_post_kb(
            giveaway.id,
            post_url=post_url,
            done=not giveaway.active)
    else:
        keyboard = kb.giveaway_kb(giveaway_id)
    await message.answer(giveaway_text,
                         reply_markup=keyboard)
