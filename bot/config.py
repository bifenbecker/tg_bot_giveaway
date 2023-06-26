import os
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR: Path = Path(os.path.abspath(__file__)).parents[1]
LOG_DIR: Path = ROOT_DIR / "logs"
WINNERS_TXT_DIR: Path = ROOT_DIR / "winners_txt"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(WINNERS_TXT_DIR, exist_ok=True)

load_dotenv(dotenv_path=(ROOT_DIR / '.env'))

SKIP_UPDATES = os.getenv("SKIP_UPDATES", default=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS"))
POST_TEMPLATES_CHANNEL_ID = int(os.getenv('POST_TEMPLATES_CHANNEL_ID', default=""))

POSTGRES_HOST = os.getenv("POSTGRES_HOST", default="localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", default=5432)
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", default="")
POSTGRES_USER = os.getenv("POSTGRES_USER", default="")
POSTGRES_DB = os.getenv("POSTGRES_DB", default="giveaway_bot")
POSTGRES_URI = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", default="")
REDIS_HOST: str = os.getenv("REDIS_HOST", default="localhost")
REDIS_PORT: str = os.getenv("REDIS_PORT", default=6379)
REDIS_FSM_DB = os.getenv("REDIS_DB_FSM", default=2)
REDIS_FSM_PREFIX = os.getenv("REDIS_PREFIX", default="fsm")
REDIS_URL: str = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/'
REDIS_FSM_URL: str = f'{REDIS_URL}{REDIS_FSM_DB}'


TORTOISE_ORM = {
    "connections": {"default": POSTGRES_URI},
    "apps": {
        "models": {
            "models": ["bot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
