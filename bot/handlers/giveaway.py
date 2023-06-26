from contextlib import suppress
import typing
import asyncio
import aiogram

from aiogram.dispatcher import FSMContext
from aiogram.types import message
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
from ._helpers import *


# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------


@dp.message_handler(lambda m: m.text == kb.btn.text_create_giveaway,
                    is_admin=True,
                    chat_type=[types.ChatType.PRIVATE],)
async def new_giveaway_start(message: types.Message, state: FSMContext):
    logger.info('Admin [{user_id}] New give start.',
                user_id=message.from_user.id)
    await st.GiveAwayState.name.set()
    async with state.proxy() as data:
        data['user_id'] = message.from_user.id
    await message.answer('Введите короткое название розыгрыша: ',
                         reply_markup=kb.cancel_kb())

# ---------------------------------------------------------------------------------


@dp.message_handler(commands={'cancel'},
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayState.name)
@dp.message_handler(lambda m: m.text == kb.btn.text_cancel,
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayState.name)
async def giveaway_set_name_cancel(message: types.Message, state: FSMContext):
    logger.info('Admin [{user_id}] New give Cancel.',
                user_id=message.from_user.id)
    await state.finish()
    await message.answer('Создание розыгрыша отменено.', reply_markup=kb.main_keyboard())


# ---------------------------------------------------------------------------------


@dp.message_handler(state=st.GiveAwayState.name,
                    is_admin=True,
                    chat_type=[types.ChatType.PRIVATE])
async def giveaway_set_name(message: types.Message, state: FSMContext):
    logger.info('Admin [{user_id}] New give name set: [{name}]',
                user_id=message.from_user.id,
                name=message.text)
    try:
        give = await models.GiveAway.create(name=message.text,
                                            author_id=message.from_user.id)
    except tortoise_exc.IntegrityError as e:
        logger.error('Error set give name: {e}', e=e)
        await message.answer('Такое название розыгрыша уже существует, попробуйте другое!')
    else:
        await state.finish()
        await message.answer('Успешно!', reply_markup=kb.main_keyboard())
        author = get_author_name(message.from_user)
        giveaway_text = page_giveaway_in(author, give.id, give.name)
        await message.answer(giveaway_text, reply_markup=kb.giveaway_kb(give.id))

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.add_post.filter(action='add'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True)
@dp.callback_query_handler(kb.cbk.add_post.filter(action=['add', 'confirm']),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True, state=st.GiveAwayPostState.post_id)
async def giveaway_add_post(query: types.CallbackQuery,
                            callback_data: typing.Dict[str, str],
                            state: FSMContext):
    current_state = await state.get_state()
    # -----------------------------------
    giveaway_id = None
    if callback_data['action'] == 'add':
        logger.info('Admin [{user_id}] Giveaway add post template. Action[add]',
                    user_id=query.from_user.id)
        if current_state:
            await state.reset_state(with_data=True)
        else:
            # Если шаблон поста уже существует оповестить
            # админа и прервать создание шаблона.
            giveaway_id = int(callback_data['giveid'])
            give_exists = await models.GiveAwayPostTemplate\
                .filter(giveaway_id=giveaway_id).exists()
            if give_exists:
                return await query.answer('Шаблон поста для гива уже существует!')
        await query.message.delete()
        await st.GiveAwayPostState.post_id.set()
        async with state.proxy() as data:
            data['giveaway_id'] = callback_data['giveid']
        await bot.send_message(query.from_user.id,
                               "Создайте рекламный пост и отправьте мне: ",
                               reply_markup=kb.cancel_kb())
    # -----------------------------------
    # Добавление спонсорского поста в базу
    # после проверки спонсоров и подтверждения
    if callback_data['action'] == 'confirm':
        logger.info('Admin [{user_id}] Giveaway add post template. Action[confirm]',
                    user_id=query.from_user.id)

        data = await state.get_data()

        # print('DATA: ', data)

        # Копируем шаблон-пост в канал-хранилище.
        saved_post = await bot.copy_message(config.POST_TEMPLATES_CHANNEL_ID,
                                            data['user_id'],
                                            data['post_id'])

        await asyncio.sleep(0.05)
        # Сохраняем данные шаблона-поста в БД
        try:
            post_template = await models.GiveAwayPostTemplate\
                .create(author_id=data['user_id'],
                        tg_message_id=saved_post.message_id,
                        tg_chat_id=config.POST_TEMPLATES_CHANNEL_ID,
                        giveaway_id=int(data['giveaway_id']),
                        post_text=data['post_text'])
        except Exception as e:
            logger.error('Error in save post_template: {e}', e=e)
            logger.info('Dump state data: ', str(data))
            # await state.finish()
            return await query.answer('Произошла ошибка запроса.')
        else:
            logger.info('Admin [{user_id}] Post template saved in DB',
                        user_id=query.from_user.id)

        added_sponsors = []

        for sponsor in data['sponsors']:
            chat_data = sponsor['chat']
            model, _ = await models.TelegramChat.get_or_create(defaults=chat_data,
                                                               pk=chat_data['id'])
            try:
                sponsor_model = await models.GiveAwaySponsor.create(
                    giveaway_id=data['giveaway_id'],
                    tg_username=chat_data['username'],
                    tg_chat_id=chat_data['id'],
                    post_template=post_template,
                    ok_permissions=sponsor['is_admin']
                )
                added_sponsors.append(
                    (sponsor_model.id, sponsor_model.tg_username)
                )
            except Exception as e:
                logger.error('Error add sposnor: {e}', e=e)

        await state.finish()
        await query.message.delete()

        text = 'Шаблон поста успешно сохранен в базе. Не удаляйте его в этом чате.'
        if added_sponsors:
            answer_list = [
                text,
                '\n',
                f"Добавлено спонсоров ({len(added_sponsors)}): \n"
            ] + [f"{x[0]}. @{x[1]}" for x in added_sponsors]
            # sponsor_count = await post_template.post_sponsors.count()
            answer_text = "\n".join(answer_list)
        else:
            answer_text = text

        await asyncio.sleep(0.05)
        await bot.send_message(data['user_id'], answer_text,
                               reply_to_message_id=data['post_id'],
                               reply_markup=kb.main_keyboard())
        logger.info('Admin [{user_id}] Sended main keboard',
                    user_id=query.from_user.id)
        # -----------------------------------
        # Формируем ответ домашней страницы конкурса
        await post_template.fetch_related('giveaway__author', 'giveaway__published_posts')
        # .annotate(sponsors_count=tfunc.Count('post_sponsors'))
        give_id = post_template.giveaway.id
        give_name = post_template.giveaway.name
        done = not post_template.giveaway.active
        posts_count = len(post_template.giveaway.published_posts)
        author = get_author_name(post_template.giveaway.author)
        sponsors_count = len(added_sponsors)
        members_count = await models.GiveAwayMember.filter(giveaway_id=give_id).count()
        giveaway_text = page_giveaway_in(author,
                                         give_id,
                                         give_name,
                                         sponsors_count=sponsors_count,
                                         templates=1,
                                         published_posts_count=posts_count,
                                         status=not done,
                                         members_count=members_count)

        await asyncio.sleep(0.05)

        await bot.send_message(data['user_id'],
                               giveaway_text,
                               reply_markup=kb.giveaway_with_post_kb(
                                   give_id, post_url=post_template.url, done=done))
        logger.info('Admin [{user_id}] Sended GiveAway[{giveaway_id}] Index page',
                    user_id=query.from_user.id, giveaway_id=give_id)

# ---------------------------------------------------------------------------------


@dp.message_handler(commands={'cancel'},
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayPostState.post_id)
@dp.message_handler(lambda m: m.text == kb.btn.text_cancel,
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayPostState.post_id)
async def giveaway_add_post_cancel(message: types.Message, state: FSMContext):

    data = await state.get_data()
    giveaway_id = data['giveaway_id']

    logger.info('Admin [{user_id}] Cancel create post template Giveaway[{giveaway_id}]',
                user_id=message.from_user.id,
                giveaway_id=giveaway_id)

    give = await models.GiveAway.filter(pk=giveaway_id).first().prefetch_related('author')

    await state.finish()
    await message.answer("Создание поста отменено!", reply_markup=kb.main_keyboard())

    author = get_author_name(give.author)
    giveaway_text = page_giveaway_in(author, give.id, give.name)

    await message.answer(giveaway_text, reply_markup=kb.giveaway_kb(give.id))

# ---------------------------------------------------------------------------------


@dp.message_handler(state=st.GiveAwayPostState.post_id,
                    chat_type=[types.ChatType.PRIVATE],
                    content_types=[types.ContentType.PHOTO, types.ContentType.TEXT])
async def giveaway_confirm_add_post(message: types.Message, state: FSMContext):
    answer_text = "Добавить этот пост для спонсоров?"
    data = await state.get_data()
    giveaway_id = data['giveaway_id']
    logger.info('Admin [{user_id}] Confirm post [{giveaway_id}]',
                user_id=message.from_user.id,
                giveaway_id=giveaway_id)
    # -----------------------------------
    # Если пользователь проигнорировал и не ответил на уже отправленное сообщение
    if (post_id := data.get('post_id', None)):
        await bot.send_message(message.from_user.id,
                               answer_text,
                               reply_to_message_id=post_id,
                               reply_markup=kb.giveaway_confirm_add_post_kb(
                                   give_away_id=giveaway_id))
        return
    # -----------------------------------
    checked_sponsors = []
    checked_result_text = [
        '.',
        answer_text,
        '\n',
        'Все спонсоры проверены: ',
        '\n'
    ]
    checked_mentions = await utils.check_chat_mentions(utils.get_mentions(message),
                                                       bot, check_admins=True)
    if checked_mentions:

        def get_text(mention, text, bold=False):
            """
            Форматирует отчет для каждого спонсора(mentions)
            """
            return f"{mention} - {md.hbold(text) if bold else md.hitalic(text)}"

        for chat_data in checked_mentions:
            chat = chat_data.get('chat')
            mention = chat_data.get('mention')
            if chat:
                checked_sponsors.append(chat_data)
                if chat_data['is_admin']:
                    text = get_text(mention, "OK", bold=True)
                else:
                    text = get_text(mention, "Недостаточно прав на постинг.")
            else:
                text = get_text(mention, "Не удалось найти канал.")
            checked_result_text.append(text)

        answer_text = "\n".join(checked_result_text)

    # -----------------------------------

    async with state.proxy() as data:
        data['post_id'] = message.message_id
        data['user_id'] = message.from_user.id
        data['sponsors'] = checked_sponsors
        data['post_text'] = message.text or message.caption or "..."

    await message.reply(answer_text,
                        reply_markup=kb.giveaway_confirm_add_post_kb(
                            give_away_id=giveaway_id))

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.add_post.filter(action='prepare'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True)
@dp.callback_query_handler(kb.cbk.send_post.filter(confirm=['yes', 'no']),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayPostPublish.chat_ids)
async def giveaway_send_post(query: types.CallbackQuery,
                             callback_data: typing.Dict[str, str],
                             state: FSMContext):

    current_state = await state.get_state()
    answer_text = None
    giveaway_post_published = False

    # -----------------------------------
    # Публикуем пост в канал спонсора или рекламный канал (для привлечения трафика)

    if callback_data['@'] == 'send_post':
        if callback_data['confirm'] == 'yes':

            async with state.proxy() as data:
                post_template_id = data['post_template_id']
                chat_id = chat_list[0] if isinstance(
                    (chat_list := data['chat_ids']), list) else chat_list
                giveaway_id = int(data['giveaway_id'])

            logger.info('Admin [{user_id}] Send post confirm Giveaway[{giveaway_id}]',
                        user_id=query.from_user.id,
                        giveaway_id=giveaway_id)

            post_template = await models.GiveAwayPostTemplate\
                .filter(pk=int(post_template_id)).prefetch_related(
                    'author', 'published_posts').first()

            if not post_template:
                logger.error('Post template not found!')
                return query.answer('Не найден шаблон поста!')

            if post_template.published_posts:
                logger.info('Admin [{user_id}] Published posts count [{count}]\
                     Giveaway[{giveaway_id}]',
                            user_id=query.from_user.id,
                            giveaway_id=giveaway_id,
                            count=len(post_template.published_posts))

            copy_from_chat_id = post_template.tg_chat_id
            copy_message_id = post_template.tg_message_id

            sponsor = await models.GiveAwaySponsor.get_or_none(
                giveaway=giveaway_id,
                tg_chat_id=chat_id
            )
            try:
                give_away_post = await bot.copy_message(
                    chat_id,
                    copy_from_chat_id,
                    copy_message_id,
                    reply_markup=kb.giveaway_user_voite_kb(
                        giveaway_id=giveaway_id)
                )
            except Exception as e:
                logger.error('Error in copy_message: {e}', e=e)
                return await query.answer('Невозможно опубликовать пост!')

            try:
                post = await models.GiveAwayPost.create(
                    tg_message_id=give_away_post.message_id,
                    tg_chat_id=chat_id,
                    template=post_template,
                    giveaway_id=giveaway_id,
                    sponsor_channel=sponsor
                )
            except Exception as e:
                logger.error('Error in post create in db: {e}', e=e)
                return await query.answer('Невозможно создать пост в базе!')

            await query.answer('Пост опубликован!')
            giveaway_post_published = True

    # -----------------------------------
    # Отправляем админу список спосноров в группу которых можно опубликовать пост
    # Также предлагаем ввести новый канал для постинга. (Не спонсора)
    answer_text = answer_text or "Выбери куда отправить"

    if callback_data['@'] == 'add_post' or \
        callback_data['confirm'] == 'no' or \
            giveaway_post_published:

        if current_state:
            state_data = await state.get_data()
            giveaway_id = state_data['giveaway_id']
            select_post_id = state_data.pop('select_post_id', -1)
            await state.reset_state(with_data=True)
        else:
            giveaway_id = int(callback_data['giveid'])
            select_post_id = -1
        
        give = await models.GiveAway.filter(pk=giveaway_id).prefetch_related(
            Prefetch("posts_templates",
                     queryset=models.GiveAwayPostTemplate.all().limit(1)),
            "sponsors").first()
        
        if not give:
            return await query.answer('Гив не найден!')
        if not give.posts_templates:
            return await query.answer('Пост - шаблон не найден!')

        await st.GiveAwayPostPublish.chat_ids.set()

        async with state.proxy() as data:
            data['giveaway_id'] = giveaway_id
            data['post_template_id'] = give.posts_templates[0].id

        await query.answer("")
        await query.message.edit_text(
            answer_text,
            reply_markup=kb.giveaway_select_sponsor_chats_kb(*give.sponsors)
        )
        if select_post_id != -1 and query.message.message_id != select_post_id:
            with suppress(Exception):
                await bot.delete_message(query.from_user.id, select_post_id)
            await asyncio.sleep(0.05)
        return await state.update_data({'select_post_id': query.message.message_id})


# ---------------------------------------------------------------------------------
@dp.callback_query_handler(lambda q: q.data == 'back',
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayPostPublish.chat_ids)
async def giveaway_send_post_cancel_query(query: types.CallbackQuery,
                                          #   callback_data: typing.Dict[str, str],
                                          state: FSMContext):
    data = await state.get_data()
    giveaway = await models.GiveAway.filter(pk=int(data['giveaway_id']))\
        .prefetch_related(Prefetch("posts_templates",
                                   queryset=models.GiveAwayPostTemplate.all().limit(1)),
                          "published_posts",
                          "sponsors",
                          "author").first()
    if not giveaway:
        return query.answer('Giveaway not found!')
    await state.finish()
    await query.message.answer('Назад', reply_markup=kb.main_keyboard())

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
    await bot.send_message(query.from_user.id,
                           giveaway_text,
                           reply_markup=kb.giveaway_with_post_kb(
                               giveaway.id, post_url=post_url,
                               done=not giveaway.active))

    await query.message.delete()

# ---------------------------------------------------------------------------------


@dp.message_handler(commands={'cancel'},
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayPostPublish.chat_ids)
@dp.message_handler(lambda m: m.text == kb.btn.text_cancel,
                    chat_type=[types.ChatType.PRIVATE],
                    state=st.GiveAwayPostPublish.chat_ids)
async def giveaway_send_post_cancel_msg(message: types.Message, state: FSMContext):
    
    data = await state.get_data()
    if not data:
        await state.finish()
        return await message.answer('Отменено', reply_markup=kb.main_keyboard())

    select_post_id = data.pop('select_post_id', None)
    giveaway_id = data['giveaway_id']

    logger.info('Admin [{user_id}] Cancel send post [{giveaway_id}]',
                user_id=message.from_user.id,
                giveaway_id=giveaway_id)

    giveaway = await models.GiveAway.filter(pk=giveaway_id).prefetch_related(
        Prefetch("posts_templates",
                 queryset=models.GiveAwayPostTemplate.all().limit(1)),
        "sponsors", "author", "published_posts").first()

    if not giveaway:
        return message.answer('Giveaway не найден!')

    await state.finish()
    await message.answer('Отмена публикации!', reply_markup=kb.main_keyboard())

    posts_count = len(giveaway.published_posts)
    author = get_author_name(giveaway.author)
    members_count = await models.GiveAwayMember.filter(giveaway_id=giveaway_id).count()
    giveaway_text = page_giveaway_in(author,
                                     giveaway.id,
                                     giveaway.name,
                                     sponsors_count=len(giveaway.sponsors),
                                     templates=1 if giveaway.posts_templates else 0,
                                     published_posts_count=posts_count,
                                     status=giveaway.active,
                                     members_count=members_count)

    post_url = temp[0].url if (temp := giveaway.posts_templates) else None
    await bot.send_message(message.from_user.id,
                           giveaway_text,
                           reply_markup=kb.giveaway_with_post_kb(
                               giveaway.id, post_url=post_url,
                               done=not giveaway.active))
    if select_post_id:
        await bot.delete_message(message.from_user.id, int(select_post_id))

# ---------------------------------------------------------------------------------


@dp.message_handler(state=st.GiveAwayPostPublish.chat_ids,
                    chat_type=[types.ChatType.PRIVATE],
                    is_admin=True)
async def giveaway_confirm_send_post_msg(message: types.Message, state: FSMContext):

    logger.info('Admin [{user_id}] Confirm send post', user_id=message.from_user.id)

    checked_mentions = await utils.check_chat_mentions(utils.get_mentions(message),
                                                       bot, check_admins=True)
    if not checked_mentions:
        text = (
            'В вашем сообщении не обнаружено ссылок на Telegram каналы.\n'
            'Пример валидной ссылки: @webbotcoder\n'
            'Попробуйте снова.'
        )
        return await message.answer(text, reply_markup=kb.cancel_kb())

    chat_data = checked_mentions[0]  # По просьбе заказчика бот не
    # публикует одновременно несколько постов

    if not chat_data['is_admin']:
        if chat_data['chat'] is None:
            err = f"Канал {chat_data['mention']} не найден!"
        else:
            err = ("У бота недостаточно прав. Напишите"
                   f" администратору канала: {chat_data['mention']}")
        text = f"Невозможно опубликовать пост.\n" + err + "\n"
        return await message.answer(text, reply_markup=kb.cancel_kb())

    async with state.proxy() as data:
        data['chat_ids'] = [chat_data['chat']['id']]

    text = (
        f"Отправить {md.hlink('пост', '@webbotcoder')}"
        f" в канал {chat_data['mention']}?\n"
        f"{md.hitalic('(Данный канал не является спонсором ГИВа.)')}"
    )

    await message.answer(text, reply_markup=kb.giveaway_confirm_send_post())

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.sponsor.filter(action='select'),
                           chat_type=[types.ChatType.PRIVATE],
                           is_admin=True,
                           state=st.GiveAwayPostPublish.chat_ids)
async def giveaway_confirm_send_post_query(query: types.CallbackQuery,
                                           callback_data: typing.Dict[str, str],
                                           state: FSMContext):
    logger.info('Admin [{user_id}] Confirm send post query', user_id=query.from_user.id)

    sponsor_id = callback_data['spid']
    sponsor = await models.GiveAwaySponsor.get(pk=sponsor_id)

    is_admin = sponsor.ok_permissions

    if not is_admin:
        mention = (await utils.check_chat_mentions([f'@{sponsor.tg_username}'],
                                                   bot, check_admins=True))[0]
        if mention['is_admin']:
            is_admin = sponsor.ok_permissions = True
            await sponsor.save()
        else:
            text = (
                'У бота недостаточно прав на постинг'
                f' в канале @{sponsor.tg_username} данного спонсора.'
                'Исправьте ошибку и попробуйте снова.'
            )
            return await query.answer(text, show_alert=True)

    async with state.proxy() as data:
        data['chat_ids'] = [sponsor.tg_chat_id]
        post_template_id = data['post_template_id']
    
    post_template = await models.GiveAwayPostTemplate.get(pk=post_template_id)
    text = (f"Отправить пост в канал @{sponsor.tg_username} спонсора?")

    await query.answer("")
    await query.message.edit_text(text, reply_markup=kb.giveaway_confirm_send_post())

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.user_voite.filter(),
                           chat_type=[types.ChatType.CHANNEL])
async def giveaway_user_voite(query: types.CallbackQuery,
                              callback_data: typing.Dict[str, str]):

    async def check_member(sp: models.GiveAwaySponsor, u: types.User) -> bool:
        member = await bot.get_chat_member(sp.tg_chat_id, u.id)
        if member['status'] not in ['member', 'creator', 'administrator']:
            return False
        return True

    giveaway_id = callback_data['gived']
    user = query.from_user
    chat = query.message.chat
    message_id = query.message.message_id

    member = await models.GiveAwayMember.get_or_none(user_id=user.id,
                                                     giveaway_id=giveaway_id)
    if member:
        return await query.answer('Вы уже участвуете!')

    give = await models.GiveAway.filter(pk=giveaway_id).prefetch_related(
        Prefetch("published_posts",
                 queryset=models.GiveAwayPost
                 .filter(tg_message_id=message_id,
                         tg_chat_id=chat.id).limit(1)),
        "sponsors"
    ).first()

    if not give:
        return await query.answer('Такого гива больше не существует!')

    if not give.active:
        return await query.answer('Данный гив завершен!')

    if not give.published_posts:
        return await query.answer('Ошибка!')

    post = give.published_posts[0]
    done = True

    for sponsor in give.sponsors:
        try:
            r = await check_member(sponsor, user)
        except aiogram_exc.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            r = await check_member(sponsor, user)
        except aiogram_exc.BadRequest as e:
            return await query.answer("")
        else:
            if not r:
                done = False
        finally:
            await asyncio.sleep(0.05)

    if not done:
        return await query.answer('Вы подписаны не на все каналы для участия в данном розыгрыше',
                                  show_alert=True)
    
    
    try:
        user_data = user.to_python()
        if user_data.get('language_code', None) is None:
            user_data['language_code'] = 'ru'
        logger.info('User data: {data}', data=user_data)
        user_model, _ = await models.TelegramUser.get_or_create(defaults=user_data, pk=user.id)
    except Exception as e:
        logger.error("Error in create user: {e}", e=e)
        return await query.answer('Ошибочка!')
    

    member_data = {'user': user_model,
                   'giveaway_id': giveaway_id,
                   'post_id': post.id}
    try:
        member = await models.GiveAwayMember.create(**member_data)
    except Exception as e:
        logger.error("Error in create member: {e}", e=e)
    else:
        logger.info('Новый участник голосования! [{user_id}]', user_id=str(user.id))

    await asyncio.sleep(0.05)
    await query.answer('Поздравляем! Теперь вы стали участником розыгрыша', show_alert=True)
    # await query.message.edit_reply_markup()
