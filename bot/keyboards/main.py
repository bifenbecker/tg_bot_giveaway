import typing
from dataclasses import dataclass
from aiogram import types
from aiogram.utils import emoji
from . import btn
from . import callbacks as cbk

InlineBtn = types.InlineKeyboardButton
Btn = types.KeyboardButton


def main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    kb.insert(btn.create_giveaway)
    kb.insert(btn.all_giveaways)
    return kb


def main_iamsub() -> types.InlineKeyboardMarkup:
    btn = InlineBtn("Я подписался", callback_data=cbk.admin.new(cmd='iamsub'))
    return types.InlineKeyboardMarkup().row(btn)


def cancel_kb() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True).row(btn.cancel)


def giveaway_list_nav_kb(index: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    back = InlineBtn(emoji.emojize(':back:'), callback_data=cbk.nav.new(
        action='givelist', value=f'{index-1}'))
    next = InlineBtn(emoji.emojize(':soon:'), callback_data=cbk.nav.new(
        action='givelist', value=f'{index+1}'))
    return kb.insert(back).insert(next)


def giveaway_kb(give_away_id: int) -> types.ReplyKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    btn_add_post = InlineBtn("Добавить пост", callback_data=cbk.add_post.new(
        action='add',
        giveid=give_away_id))
    kb.insert(btn_add_post)
    return kb


def giveaway_with_post_kb(give_away_id: int,
                          post_url: typing.Optional[str] = None,
                          export: bool = True,
                          winner: bool = True,
                          done: bool = False) -> types.ReplyKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    if not done:
        btn_send_post = InlineBtn("Опубликовать пост", callback_data=cbk.add_post.new(
            action='prepare',
            giveid=give_away_id))
        kb.insert(btn_send_post)
    if post_url:
        btn_url = InlineBtn(text='Перейти к посту', url=post_url)
        kb.row(btn_url)
    if winner and not done:
        btn_winner = InlineBtn(text='Завершить Give', callback_data=cbk.winner.new(
            action='prepare', value=give_away_id))
        kb.row(btn_winner)
    if export:
        btn_export = InlineBtn(text='Скачать', callback_data=cbk.export.new(
            action='prepare', value=give_away_id))
        kb.row(btn_export)
    return kb


def giveaway_confirm_add_post_kb(give_away_id: int) -> types.ReplyKeyboardMarkup:
    btn_yes = InlineBtn("Да", callback_data=cbk.add_post.new(
        action='confirm',
        giveid=give_away_id))
    btn_no = InlineBtn("Нет", callback_data=cbk.add_post.new(
        action='add',
        giveid=give_away_id))
    return types.InlineKeyboardMarkup(row_width=2).insert(btn_yes).insert(btn_no)


def giveaway_select_sponsor_chats_kb(*sponsors) -> types.ReplyKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)

    def btn_sponsor(text, id):
        return InlineBtn(text,
                         callback_data=cbk.sponsor.new(action='select', spid=id))
    for sp in sponsors:
        btn = btn_sponsor(f"@{sp.tg_username}", sp.id)
        kb.insert(btn)
    kb.row(InlineBtn('<< Назад', callback_data='back'))
    return kb


def giveaway_confirm_send_post():
    btn_yes = InlineBtn("Да", callback_data=cbk.send_post.new(confirm='yes'))
    btn_no = InlineBtn("Нет", callback_data=cbk.send_post.new(confirm='no'))
    return types.InlineKeyboardMarkup(row_width=2).insert(btn_yes).insert(btn_no)


def giveaway_user_voite_kb(giveaway_id: int, text: str = "Участвовать"):
    btn_voite = InlineBtn(
        text, callback_data=cbk.user_voite.new(gived=giveaway_id))
    return types.InlineKeyboardMarkup(row_width=3).row(btn_voite)


def giveaway_members_export():
    kb = types.InlineKeyboardMarkup(row_width=2)
    btn_txt = InlineBtn('Участники (txt)',
                        callback_data=cbk.export.new(action='download',
                                                     value='members_txt'))
    btn_back = InlineBtn('<< Назад',
                         callback_data=cbk.export.new(action='nav', value='back'))
    kb.insert(btn_txt)
    return kb.row(btn_back)


def giveaway_set_winner_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    btn_by_id = InlineBtn('Выбрать по ID',
                          callback_data=cbk.winner.new(action='set',
                                                       value='id'))
    btn_by_username = InlineBtn('Выбрать по Username',
                                callback_data=cbk.winner.new(action='set',
                                                             value='username'))
    btn_random = InlineBtn('Случайно',
                           callback_data=cbk.winner.new(action='set',
                                                        value='random'))
    # NEW:
    btn_finish = InlineBtn('Завершить GiVe',
                           callback_data=cbk.winner.new(action='cmd',
                                                        value='finish'))
    btn_back = InlineBtn('<< Назад',
                         callback_data=cbk.winner.new(action='nav', value='back'))
    kb.row(btn_random)
    kb.row(btn_by_id)
    kb.row(btn_by_username)
    kb.row(btn_finish)
    return kb.row(btn_back)


def giveaway_set_winner_confirm_kb():
    btn_yes = InlineBtn("Да", callback_data=cbk.winner.new(
        action='confirm', value='yes'))
    btn_no = InlineBtn("Нет", callback_data=cbk.winner.new(
        action='confirm', value='no'))
    return types.InlineKeyboardMarkup(row_width=2).insert(btn_yes).insert(btn_no)


def giveaway_finish_confirm_kb():
    btn_yes = InlineBtn("Да", callback_data=cbk.winner.new(
        action='cmd', value='finish_confirm'))
    btn_no = InlineBtn("Нет", callback_data=cbk.winner.new(
        action='confirm', value='no'))
    return types.InlineKeyboardMarkup(row_width=2).insert(btn_yes).insert(btn_no)


@dataclass
class GiveAwayKb:
    giveaway_id: typing.Union[int, str]

    def __post_init__(self, ):
        pass
