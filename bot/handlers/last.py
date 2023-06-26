from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import CommandHelp, CommandStart, Command, Text
from aiogram.utils.emoji import emojize, demojize
from aiogram import types, md
from loguru import logger
from bot.keyboards import btn

from bot.misc import dp, bot
from bot import config, keyboards as kb, states as st
from bot import models


@dp.message_handler(commands={'cancel'},
                    chat_type=[types.ChatType.PRIVATE],
                    is_admin=True,
                    state='*')
@dp.message_handler(lambda m: m.text == btn.text_cancel,
                    chat_type=[types.ChatType.PRIVATE],
                    is_admin=True,
                    state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('No state for cancel', reply_markup=kb.main_keyboard())
        return
    logger.info(f'Cancel State: {current_state}')
    data = await state.get_data()
    logger.info(f'Cancel State data: {data}')
    await state.finish()
    await message.answer("Действие отменено", reply_markup=kb.main_keyboard())
