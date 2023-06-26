from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "telegramchat" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "type" VARCHAR(50) NOT NULL,
    "title" VARCHAR(128),
    "username" VARCHAR(100),
    "first_name" VARCHAR(100),
    "last_name" VARCHAR(100),
    "bio" TEXT,
    "description" TEXT,
    "invite_link" VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS "telegramuser" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(32)  UNIQUE,
    "is_bot" BOOL NOT NULL  DEFAULT False,
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "language_code" VARCHAR(10) NOT NULL
);
CREATE TABLE IF NOT EXISTS "giveaway" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "active" BOOL NOT NULL  DEFAULT True,
    "author_id" BIGINT NOT NULL REFERENCES "telegramuser" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "giveawayposttemplate" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tg_message_id" INT NOT NULL,
    "tg_chat_id" BIGINT NOT NULL,
    "post_text" TEXT NOT NULL,
    "url" VARCHAR(150),
    "author_id" BIGINT NOT NULL REFERENCES "telegramuser" ("id") ON DELETE CASCADE,
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveawaypos_tg_mess_f30f49" UNIQUE ("tg_message_id", "tg_chat_id", "giveaway_id")
);
CREATE TABLE IF NOT EXISTS "giveawaysponsor" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tg_username" VARCHAR(100) NOT NULL,
    "tg_chat_id" BIGINT NOT NULL,
    "ok_permissions" BOOL NOT NULL  DEFAULT False,
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    "post_template_id" INT NOT NULL REFERENCES "giveawayposttemplate" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveawayspo_tg_chat_9cd5da" UNIQUE ("tg_chat_id", "giveaway_id")
);
CREATE TABLE IF NOT EXISTS "giveawaypost" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tg_message_id" BIGINT NOT NULL,
    "tg_chat_id" BIGINT NOT NULL,
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    "sponsor_channel_id" INT REFERENCES "giveawaysponsor" ("id") ON DELETE CASCADE,
    "template_id" INT NOT NULL REFERENCES "giveawayposttemplate" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveawaypos_tg_mess_e0db24" UNIQUE ("tg_message_id", "tg_chat_id")
);
CREATE TABLE IF NOT EXISTS "giveawaymember" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    "post_id" INT NOT NULL REFERENCES "giveawaypost" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "telegramuser" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveawaymem_user_id_08d962" UNIQUE ("user_id", "giveaway_id")
);
CREATE TABLE IF NOT EXISTS "giveawaywinner" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "username" VARCHAR(32),
    "giveaway_id" INT NOT NULL REFERENCES "giveaway" ("id") ON DELETE CASCADE,
    "member_id" INT NOT NULL REFERENCES "giveawaymember" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_giveawaywin_member__e1c27a" UNIQUE ("member_id", "giveaway_id"),
    CONSTRAINT "uid_giveawaywin_member__487072" UNIQUE ("member_id", "giveaway_id", "user_id")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
