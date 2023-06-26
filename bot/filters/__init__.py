from aiogram import Dispatcher


def setup(dp: Dispatcher):
    from .admin import isAdmin

    dp.filters_factory.bind(isAdmin)
