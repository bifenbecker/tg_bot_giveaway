import typing
from enum import unique
from tortoise import fields
from tortoise.signals import post_delete, post_save, pre_delete, pre_save
from .db import BaseModel, TimedBaseModel


class GiveAway(TimedBaseModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, null=False, unique=True)
    author = fields.ForeignKeyField(
        'models.TelegramUser', related_name='giveaways', null=False)
    active = fields.BooleanField(default=True)


class GiveAwayPostTemplate(TimedBaseModel):
    id = fields.IntField(pk=True)
    tg_message_id = fields.IntField(null=False)
    tg_chat_id = fields.BigIntField(null=False)
    post_text = fields.TextField(null=False)
    author = fields.ForeignKeyField(
        'models.TelegramUser', related_name='posts_templates', null=False)
    giveaway = fields.ForeignKeyField(
        'models.GiveAway', related_name='posts_templates', null=False)
    url = fields.CharField(max_length=150, null=True)

    class Meta:
        unique_together = (
            ("tg_message_id", "tg_chat_id", "giveaway"),
        )


@pre_save(GiveAwayPostTemplate)
async def post_template_signal_pre_save(
        sender: "typing.Type[GiveAwayPostTemplate]",
        instance: GiveAwayPostTemplate,
        using_db,
        update_fields) -> None:
    try:
        url = f"https://t.me/c/{str(instance.tg_chat_id)[3:]}/{instance.tg_message_id}"
    except:
        url = ""
    instance.url = url


class GiveAwaySponsor(TimedBaseModel):
    id = fields.IntField(pk=True)
    giveaway = fields.ForeignKeyField('models.GiveAway',
                                      related_name='sponsors', null=False)
    tg_username = fields.CharField(100, null=False)
    tg_chat_id = fields.BigIntField(null=False)
    post_template = fields.ForeignKeyField(
        'models.GiveAwayPostTemplate', related_name='post_sponsors', null=False)
    ok_permissions = fields.BooleanField(default=False, null=False)

    class Meta:
        unique_together = (
            ("tg_chat_id", "giveaway"),
        )


class GiveAwayPost(TimedBaseModel):
    id = fields.IntField(pk=True)
    tg_message_id = fields.BigIntField(null=False)  # real message_id from chat
    tg_chat_id = fields.BigIntField(null=False)  # real chat_id
    template = fields.ForeignKeyField(
        'models.GiveAwayPostTemplate', related_name='published_posts', null=False)
    giveaway = fields.ForeignKeyField(
        'models.GiveAway', related_name='published_posts', null=False)
    sponsor_channel = fields.ForeignKeyField('models.GiveAwaySponsor',
                                             related_name='published_posts', null=True)

    class Meta:
        unique_together = (
            ("tg_message_id", "tg_chat_id"),
        )


class GiveAwayMember(TimedBaseModel):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.TelegramUser', null=False)
    giveaway = fields.ForeignKeyField(
        'models.GiveAway', related_name='members', null=False)
    post = fields.ForeignKeyField(
        'models.GiveAwayPost', related_name='members', null=False)

    class Meta:
        unique_together = (
            ("user", "giveaway"),
        )


class GiveAwayWinner(TimedBaseModel):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(null=False)
    username = fields.CharField(32, null=True, unique=False)
    member = fields.ForeignKeyField(
        'models.GiveAwayMember', null=False, related_name='winners')
    giveaway = fields.ForeignKeyField(
        'models.GiveAway', related_name='winner', null=False)

    class Meta:
        unique_together = (
            ("member", "giveaway"),
            ("member", "giveaway", "user_id"),
        )
