from bot.misc import setup, runner
from bot import logging

logging.setup()
setup()
runner.start_polling()