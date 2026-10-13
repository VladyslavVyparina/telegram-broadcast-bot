import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    default_language: str
    database_path: str
    timezone: str

    @classmethod
    def from_values(
        cls,
        *,
        bot_token: str,
        admin_id: int,
        default_language: str = "ar",
        database_path: str = "bot.db",
        timezone: str = "Asia/Riyadh",
    ) -> "Config":
        return cls(
            bot_token=bot_token,
            admin_id=admin_id,
            default_language=default_language or "ar",
            database_path=database_path,
            timezone=timezone,
        )


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is required in .env")

    admin_raw = os.getenv("ADMIN_ID", "").strip()
    if not admin_raw:
        raise ValueError("ADMIN_ID is required in .env")

    return Config(
        bot_token=token,
        admin_id=int(admin_raw),
        default_language=os.getenv("DEFAULT_LANGUAGE", "ar").strip() or "ar",
        database_path=os.getenv("DATABASE_PATH", "bot.db").strip() or "bot.db",
        timezone=os.getenv("BOT_TIMEZONE", "Asia/Riyadh").strip() or "Asia/Riyadh",
    )
