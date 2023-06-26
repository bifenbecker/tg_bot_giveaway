import asyncio
from typing import List, Optional, Union
from aiogram.utils.markdown import link
from aiogram import types, Bot
from aiogram.utils.exceptions import ChatNotFound
import typing


def get_user_link(user_id: Union[str, int], text: Optional[str] = None) -> str:
    if not text:
        text = user_id
    return link(str(text), f"tg://user?id={user_id}")


def get_mentions(message: types.Message) -> typing.List[str]:
    mentions = []
    if message.content_type == types.ContentType.PHOTO:
        entity_text = message.caption
        entities = message.caption_entities
    elif message.content_type == types.ContentType.TEXT:
        entity_text = message.text
        entities = message.entities
    else:
        entity_text = None
    if entity_text:
        for entity in entities:
            if entity['type'] == 'mention':
                mentions.append(entity.get_text(entity_text))
    return mentions


async def check_admin_permissons(mention, bot: Bot):
    admins = []
    try:
        await asyncio.sleep(0.05)
        admins = await bot.get_chat_administrators(mention)
    except Exception as e:
        pass
    if admins:
        for data in admins:
            if (await bot.me)['id'] == data['user']['id']:
                if data['can_post_messages']:
                    return True, data.to_python()
    return False, None


async def check_chat_mentions(mentions, bot: Bot, check_admins=False):
    r = []
    mentions = set(mentions)
    for mention in mentions:
        err = None
        chat = None
        try:
            chat = await bot.get_chat(mention)
        except ChatNotFound:
            err = "Канал не найден!"
        except Exception as e:
            err = str(e)

        report = dict(
            mention=mention,
            chat=chat.to_python() if chat else None,
            # err=err
        )
        if check_admins:
            if chat:
                is_admin, per = await check_admin_permissons(mention, bot)
            else:
                is_admin = False
                per = None
            report['is_admin'] = is_admin
            report['permissons'] = per
        # await asyncio.sleep(0.01)
        r.append(report)
    return r
