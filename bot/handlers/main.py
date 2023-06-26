import asyncio
from loguru import logger
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

TEMPLATES_CHANNEL_ID = int(config.POST_TEMPLATES_CHANNEL_ID)


async def need_template_channel_sub_text():
    """
    Получает пригласительную ссылку для канала-хранилища и возвращает ее
    в тексте спросьбой подписки на канал. Необходимо для администраторов бота.
    """
    try:
        chat_link = await bot.export_chat_invite_link(TEMPLATES_CHANNEL_ID)
    except aiogram_exc.BadRequest:
        text = "Произошла ошибка приполучении пригласительной ссылки!"
    else:
        text = (
            "Вы администратор бота!\n"
            "Вам необходимо подписаться на канал-хранилище всех постов гива."
            "Он находится по ссылке ниже: \n\n"
            f"{chat_link}\n\n"
            "После подписки нажмите на кнопку: Я подписался."
        )
    return text


@dp.message_handler(CommandStart(), chat_type=[types.ChatType.PRIVATE], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    if (user := message.from_user).id in config.ADMIN_IDS:
        await models.TelegramUser.get_or_create(defaults=user.to_python(),
                                                pk=user.id)
        try:
            member = await bot.get_chat_member(TEMPLATES_CHANNEL_ID, user.id)
        except aiogram_exc.BadRequest as e:
            logger.error("Error: {e}", e=e)
            return await message.answer('Произошла ошибка!')
        else:
            if member['status'] in ['creator', 'administrator']:
                if not member['can_edit_messages']:
                    r = await bot.promote_chat_member(TEMPLATES_CHANNEL_ID,
                                                        user.id, can_edit_messages=True)
                    if not r:
                        text = (
                            'Вы являетесь администратором канала, но у вас '
                            'недостаточно прав для редактирования постов.'
                        )
                        return await message.answer(text)
            else:
                await asyncio.sleep(0.05)
                text = await need_template_channel_sub_text()
                await st.AdminTemplatesSubState.not_sub.set()
                return await message.answer(text, reply_markup=kb.main_iamsub())

        await message.answer("Добро пожаловать.",
                             reply_markup=kb.main_keyboard())
    else:
        await message.answer("У вас нет соответствующих прав для использования бота.")

# ---------------------------------------------------------------------------------


@dp.callback_query_handler(kb.cbk.admin.filter(cmd='iamsub'),
                           is_admin=True,
                           chat_type=[types.ChatType.PRIVATE],
                           state=st.AdminTemplatesSubState.not_sub)
async def channel_message(query: types.CallbackQuery, state: FSMContext):
    try:
        r = await bot.promote_chat_member(TEMPLATES_CHANNEL_ID,
                                          query.from_user.id, can_edit_messages=True)
    except aiogram_exc.BadRequest:
        return await query.answer("Вы не подписались на канал-хранилище!", show_alert=True)
    if r:
        await state.finish()
        await query.answer('Вы назначены администратором канала-хранилище!', show_alert=True)
        await asyncio.sleep(0.1)
        await query.message.answer("Добро пожаловать.", reply_markup=kb.main_keyboard())
        await query.message.delete()
    else:
        await query.answer('Произошла ошибка! Напишите разработчику.')
# ---------------------------------------------------------------------------------


@dp.message_handler(chat_type=[types.ChatType.PRIVATE],
                    is_admin=True, state=st.AdminTemplatesSubState.not_sub)
async def not_subscription_to_post_channel(message: types.Message):
    text = await need_template_channel_sub_text()
    await message.answer(text, reply_markup=kb.main_iamsub())


@dp.message_handler(commands={'help'}, chat_type=[types.ChatType.PRIVATE], is_admin=True)
async def cmd_help(message: types.Message):

    commands_list = """
    /start - отправьте команду start, чтобы начать
    /cancel - отменить команду, если например бот зациклился.
    """

    await message.answer(commands_list)
# ---------------------------------------------------------------------------------
