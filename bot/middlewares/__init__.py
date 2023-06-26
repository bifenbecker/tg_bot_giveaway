from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Dispatcher



def setup(dp: Dispatcher):
    dp.middleware.setup(LoggingMiddleware("bot"))