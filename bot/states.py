from aiogram.dispatcher.filters.state import State, StatesGroup


class AdminTemplatesSubState(StatesGroup):
    not_sub = State()


class GiveAwayState(StatesGroup):
    user_id = State()
    name = State()


class GiveAwayPostState(StatesGroup):
    post_text = State()
    sponsors = State()
    giveaway_id = State()
    post_id = State()
    user_id = State()


class GiveAwayPostPublish(StatesGroup):
    select_post_id = State()
    giveaway_id = State()
    post_template_id = State()
    chat_ids = State()


class GiveAwayExportState(StatesGroup):
    giveaway_id = State()
    type = State()
    value = State()

class GiveAwayWinnerState(StatesGroup):
    giveaway_id = State()
    user = State()
    user_id = State()
    user_name = State()
    random = State()
    # finish = State()
