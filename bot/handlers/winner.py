import typing
import asyncio

import random
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


async def finish_giveaway_text(give_id):
    winners = await models.GiveAwayWinner.filter(giveaway_id=give_id).all()
    winners_text = []

    for winner in winners:
        winners_text.append(f" -  @{winner.username}")

    winners_count = len(winners)
    if winners_count == 0:
        texts = [
            "Для завершения GiveAway необходимо определить победителя.",
            "Выберите ниже как хотите назначить победителя:"
        ]
    else:
        texts = [
            f"Кол-во найденных победителей - {winners_count} :",
            f', \n'.join(winners_text), ""
            "Вы можете завершить данный GiveAway или добавить еще одного победителя:"
        ]
    return texts


@dp.callback_query_handler(kb.cbk.winner.filter(action='prepare'),
                           chat_type=[types.ChatType.PRIVATE], is_admin=True)
@dp.callback_query_handler(kb.cbk.winner.filter(action='confirm', value='no'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=[st.GiveAwayWinnerState.user_id,
                                  st.GiveAwayWinnerState.user_name,
                                  st.GiveAwayWinnerState.random])
async def winner_index(query: types.CallbackQuery,
                       callback_data: typing.Dict[str, str],
                       state: FSMContext):

    logger.info("Admin [{user_id}] in winner index page",
                user_id=query.from_user.id)

    if (await state.get_state()):
        giveaway_id = (await state.get_data())['giveaway_id']
        await state.reset_state()
    else:
        giveaway_id = int(callback_data['value'])

    await st.GiveAwayWinnerState.user.set()

    async with state.proxy() as data:
        data['giveaway_id'] = giveaway_id

    await query.answer("")
    await asyncio.sleep(0.05)

    texts = await finish_giveaway_text(giveaway_id)

    await query.message.edit_text("\n".join(texts),
                                  reply_markup=kb.giveaway_set_winner_kb())
# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.winner.filter(action='nav', value='back'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayWinnerState.user)
async def winner_back_to_giveaway(query: types.CallbackQuery,
                                  callback_data: typing.Dict[str, str],
                                  state: FSMContext):

    logger.info('Admin [{user_id}] back to GiveAway index page',
                user_id=query.from_user.id)

    await query.answer("")
    data = await state.get_data()

    try:
        giveaway = await models.GiveAway.filter(pk=int(data['giveaway_id']))\
            .prefetch_related(Prefetch("posts_templates",
                                       queryset=models.GiveAwayPostTemplate.all().limit(1)),
                              "sponsors", "published_posts",
                              "author").first()
    except Exception as e:
        logger.error("winner_back_to_giveaway error: {e}", e=e)
        giveaway = None

    if not giveaway:
        return query.answer('GiveAway не найден!')

    await state.finish()

    posts_count = len(giveaway.published_posts)
    author = get_author_name(giveaway.author)
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


@dp.callback_query_handler(kb.cbk.winner.filter(action='set'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=[st.GiveAwayWinnerState.user])
async def winner_select_query(query: types.CallbackQuery,
                              callback_data: typing.Dict[str, str],
                              state: FSMContext):

    data = await state.get_data()
    giveaway_id = int(data['giveaway_id'])
    chat_id = query.from_user.id

    method = callback_data['value']
    not_members_text = 'У данного гива нет участников!'

    logger.info("Select winner in giveaway id[{giveaway_id}]. Method: {method}",
                giveaway_id=giveaway_id, method=method)

    if (await models.GiveAwayMember.filter(giveaway_id=giveaway_id).count() == 0):
        return await query.answer(not_members_text)

    await query.answer("")

    if method == 'id':
        await st.GiveAwayWinnerState.user_id.set()
        await query.message.delete()
        await bot.send_message(chat_id, "Введите id участника: ",
                               reply_markup=kb.cancel_kb())

    elif method == 'username':
        await st.GiveAwayWinnerState.user_name.set()
        await query.message.delete()
        await bot.send_message(chat_id, "Введите username участника: ",
                               reply_markup=kb.cancel_kb())

    elif method == 'random':
        await st.GiveAwayWinnerState.random.set()
        member_ids = [x[0] for x in await models.GiveAwayMember
                      .filter(giveaway_id=giveaway_id).values_list('id')]
        random.shuffle(member_ids)
        winner_id = member_ids[random.randint(0, len(member_ids)-1)]

        winner = await models.GiveAwayMember.filter(pk=winner_id)\
            .prefetch_related('user').first()

        user_id = winner.user.id
        username = f"@{u}" if (u := winner.user.username) else " - "
        keyboard = kb.giveaway_set_winner_confirm_kb()
        texts = [
            "Победитель определен случайно: ",
            md.hbold("Username: ") + username,
            md.hbold("ID: ") + str(user_id) + "\n",
            "Утвердить данного участника на роль победителя?"
        ]
        await state.update_data(dict(user={
            'id': winner.user.id,
            'username': winner.user.username,
            'member_id': winner.id
        }))
        await query.message.edit_text("\n".join(texts), reply_markup=keyboard)

# ---------------------------------------------------------------------------------


@dp.message_handler(commands={'cancel'},
                    chat_type=[types.ChatType.PRIVATE],
                    state=[st.GiveAwayWinnerState.user_name,
                           st.GiveAwayWinnerState.user_id])
@dp.message_handler(lambda m: m.text == kb.btn.text_cancel,
                    chat_type=[types.ChatType.PRIVATE],
                    state=[st.GiveAwayWinnerState.user_name,
                           st.GiveAwayWinnerState.user_id])
async def winner_select_cancel_msg(message: types.Message, state: FSMContext):
    logger.info("Admin [{user_id}] cancel select winner",
                user_id=message.from_user.id)

    await st.GiveAwayWinnerState.user.set()
    await message.answer('Отменено', reply_markup=kb.main_keyboard())
    giveaway_id = (await state.get_data())['giveaway_id']
    texts = await finish_giveaway_text(giveaway_id)
    await message.answer("\n".join(texts), reply_markup=kb.giveaway_set_winner_kb())

# ---------------------------------------------------------------------------------


@dp.message_handler(chat_type=[types.ChatType.PRIVATE],
                    is_admin=True,
                    state=[st.GiveAwayWinnerState.user_name,
                           st.GiveAwayWinnerState.user_id])
async def winner_select_msg(message: types.Message, state: FSMContext):

    current_state = await state.get_state()
    data = await state.get_data()
    giveaway_id = int(data['giveaway_id'])
    username = user_id = None
    prefix = "UNKNOWN"

    if (current_state := await state.get_state()) == 'GiveAwayWinnerState:user_name':
        prefix = "Username"
        if (mentions := utils.get_mentions(message)):
            username = mentions[0][1:]
        elif (text := message.text):
            username = u[1:] if (u := text).startswith('@') else u

    elif current_state == 'GiveAwayWinnerState:user_id':
        prefix = "ID"
        if (text_id := message.text):
            with suppress(ValueError):
                user_id = int(text_id)

    if user_id or username:
        try:
            winner = models.GiveAwayMember.filter(giveaway_id=giveaway_id)

            if username:
                logger.info("Search USERNAME: @{username} in Giveaway id[{giveaway_id}]",
                            username=username, giveaway_id=giveaway_id)
                winner = winner.filter(user__username=username)

            if user_id:
                logger.info("Search USER_ID: {user_id} in Giveaway id[{giveaway_id}]",
                            user_id=user_id, giveaway_id=giveaway_id)
                winner = winner.filter(user__id=user_id)

            winner = await winner.prefetch_related('user').first()

        except tortoise_exc.IntegrityError as e:
            logger.error("Error in filter member: {e}", e=e)

        if winner:
            username = f"@{u}" if (u := winner.user.username) else " - "

            await state.update_data(dict(user={
                'id': winner.user.id,
                'username': winner.user.username,
                'member_id': winner.id
            }))

            logger.info('User [@{username} | {user_id}] founded in GiveAway [{giveaway_id}]',
                        username=username,
                        user_id=user_id,
                        giveaway_id=giveaway_id)

            texts = [
                "Участник найден в базе: ",
                md.hbold("Username: ") + f"@{username}",
                md.hbold("ID: ") + str(winner.user.id) + "\n",
                "Утвердить данного участника на роль победителя?"
            ]

            keyboard = kb.giveaway_set_winner_confirm_kb()
            return await message.answer("\n".join(texts), reply_markup=keyboard)

    text = (
        f"Участник: [{prefix}: {username or user_id or message.text}]"
        " не найден. Попробуйте снова: "
    )
    await message.answer(text, reply_markup=kb.cancel_kb())


# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.winner.filter(action='confirm', value='yes'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=[st.GiveAwayWinnerState.user_id,
                                  st.GiveAwayWinnerState.user_name,
                                  st.GiveAwayWinnerState.random])
async def winner_confirm(query: types.CallbackQuery,
                         callback_data: typing.Dict[str, str],
                         state: FSMContext):

    data = await state.get_data()

    giveaway_id = int(data['giveaway_id'])
    member_id = data['user']['member_id']
    username = data['user']['username']
    user_id = data['user']['id']

    logger.info('Confirm winner [{username}]!', username=username)

    data = dict(
        giveaway_id=giveaway_id,
        member_id=member_id,
        user_id=user_id,
        username=username
    )

    exists = await models.GiveAwayWinner.get_or_none(member_id=member_id, giveaway_id=giveaway_id)
    if exists:
        return await query.answer('Такой победитель уже существует! Выберите другого!')

    winner = await models.GiveAwayWinner.create(**data)
    await query.answer(f'Участник {winner.username} добавлен в список победителей!')

    await state.reset_state(True)
    await state.update_data(giveaway_id=giveaway_id)
    await st.GiveAwayWinnerState.user.set()

    texts = await finish_giveaway_text(giveaway_id)
    await query.message.edit_text("\n".join(texts), reply_markup=kb.giveaway_set_winner_kb())


# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.winner.filter(action='cmd', value='finish'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayWinnerState)
async def confirm_finish_giveaway(query: types.CallbackQuery,
                                  callback_data: typing.Dict[str, str],
                                  state: FSMContext):

    logger.info('Admin [{user_id}] confirm a GiveAway finished?!',
                user_id=query.from_user.id)
    giveaway_id = (await state.get_data())['giveaway_id']
    winners_count = await models.GiveAwayWinner.filter(giveaway_id=giveaway_id).count()
    if winners_count == 0:
        return await query.answer('Сначала определите победителя!')

    await query.answer('')
    await st.GiveAwayWinnerState.user_id.set()
    await query.message.edit_text('Вы действительно хотите завершить GiveAway?',
                                  reply_markup=kb.giveaway_finish_confirm_kb())


# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.winner.filter(action='cmd', value='finish_confirm'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=[st.GiveAwayWinnerState.user_id,
                                  st.GiveAwayWinnerState.user_name,
                                  st.GiveAwayWinnerState.random])
async def finish_giveaway(query: types.CallbackQuery,
                          callback_data: typing.Dict[str, str],
                          state: FSMContext):

    data = await state.get_data()

    giveaway_id = int(data['giveaway_id'])
    winners = await models.GiveAwayWinner.filter(giveaway_id=giveaway_id).all()

    usernames = [f"@{x.username}" for x in winners]
    winner_text = "Победитель: " if len(usernames) == 1 else "Победители: "
    winner_text += usernames[0] if len(
        usernames) == 1 else ", ".join(usernames)

    logger.info('This GiveAway finished!')

    await state.finish()

    # ---------------------------------------------------------------
    # Дальше идет вывод
    giveaway = await models.GiveAway.get(pk=giveaway_id)
    giveaway.active = False
    await giveaway.save()

    # -----------------------------------
    sponsors_chat_ids = await models.GiveAwaySponsor.filter(giveaway_id=giveaway_id)\
        .values_list('tg_chat_id')
    sponsors_chat_ids = [x[0] for x in sponsors_chat_ids]
    posts = await models.GiveAwayPost.filter(giveaway_id=giveaway_id)\
        .prefetch_related("template").all().order_by("-created_at")

    async def update_message(texts: typing.List, chat_id: int, message_id: int):
        try:
            logger.info('Update message: {msg}', msg="\n".join(texts))
            logger.info('Update chat_id: {chat_id}', chat_id=chat_id)
            logger.info('Update message_id: {msg_id}', msg_id=message_id)
            # return await bot.edit_message_text("\n".join(texts),
            #                                    chat_id=chat_id,
            #                                    message_id=message_id)
            return await bot.edit_message_caption(chat_id=chat_id,
                                                  message_id=message_id, 
                                                  caption="\n".join(texts))
        except Exception as e:
            logger.error("Error in update sponsor message: {e}", e=e)
        except aiogram_exc.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            return await update_message(texts=texts, chat_id=chat_id, message_id=message_id)

    for post in posts:
        texts = [
            post.template.post_text, "\n", "- "*20,
            "Конкурс завершен.",
            winner_text
        ]

        if post.tg_chat_id in sponsors_chat_ids:
            logger.info("Update sponsor message: {url}",
                        url=f"https://t.me/c/{str(post.tg_chat_id)[3:]}/{post.tg_message_id}")
            update = await update_message(texts,
                                          chat_id=post.tg_chat_id,
                                          message_id=post.tg_message_id)
            index = sponsors_chat_ids.index(post.tg_chat_id)
            sponsors_chat_ids.pop(index)
            await asyncio.sleep(0.05)

    # -----------------------------------

    await query.answer('Данный гив завершен!')

    logger.info('Admin [{user_id}] back to GiveAway index page',
                user_id=query.from_user.id)

    giveaway = await models.GiveAway.filter(pk=giveaway_id)\
        .prefetch_related(Prefetch("posts_templates",
                                   queryset=models.GiveAwayPostTemplate.all().limit(1)),
                          "sponsors", "published_posts",
                          "author").first()
    await state.finish()

    posts_count = len(giveaway.published_posts)
    author = get_author_name(giveaway.author)
    members_count = await models.GiveAwayMember.filter(giveaway_id=giveaway_id).count()
    giveaway_text = page_giveaway_in(author,
                                     giveaway.id,
                                     giveaway.name,
                                     sponsors_count=len(giveaway.sponsors),
                                     templates=1 if giveaway.posts_templates else 0,
                                     published_posts_count=posts_count,
                                     status=False,
                                     members_count=members_count,
                                     winner=', '.join(usernames))

    post_url = temp[0].url if (temp := giveaway.posts_templates) else None

    await query.message.edit_text(giveaway_text,
                                  reply_markup=kb.giveaway_with_post_kb(
                                      giveaway.id, post_url=post_url,
                                      done=True))
