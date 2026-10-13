import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(".env.public")
load_dotenv(".env")

SUBSCRIPTION_OWNER_IDS: frozenset[int] = frozenset({
    929743223,
    8734758541,
    865883330,
})

PLATFORM_ADMIN_IDS: frozenset[int] = SUBSCRIPTION_OWNER_IDS

# Telegram Stars from payments go to the bot balance in Telegram.
# This ID is the primary finance contact (notifications + balance hints).
STARS_OWNER_ID: int = int(os.getenv("STARS_OWNER_ID", "929743223").strip() or "929743223")


def is_platform_owner(user_id: int) -> bool:
    return user_id in SUBSCRIPTION_OWNER_IDS


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    default_language: str
    database_path: str
    timezone: str
    clones_dir: str
    wallet_pay_api_key: str
    wallet_pay_webhook_host: str
    wallet_pay_webhook_port: int
    wallet_pay_webhook_path: str
    wallet_pay_return_url: str
    wallet_pay_order_timeout: int
    crypto_pay_api_token: str
    crypto_pay_testnet: bool
    crypto_pay_webhook_path: str
    crypto_pay_order_timeout: int
    crypto_pay_return_url: str

    @property
    def wallet_pay_enabled(self) -> bool:
        return bool(self.wallet_pay_api_key)

    @property
    def crypto_pay_enabled(self) -> bool:
        return bool(self.crypto_pay_api_token)


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is required in .env.public")

    admin_raw = os.getenv("ADMIN_ID", "").strip()
    if not admin_raw:
        raise ValueError("ADMIN_ID is required in .env.public")

    platform_bot = os.getenv("PLATFORM_BOT_USERNAME", "Ni_iF7Fibot").strip().lstrip("@")
    default_return = f"https://t.me/{platform_bot}"

    return Config(
        bot_token=token,
        admin_id=int(admin_raw),
        default_language=os.getenv("DEFAULT_LANGUAGE", "ar").strip() or "ar",
        database_path=os.getenv("DATABASE_PATH", "bot_public.db").strip() or "bot_public.db",
        timezone=os.getenv("BOT_TIMEZONE", "Asia/Riyadh").strip() or "Asia/Riyadh",
        clones_dir=os.getenv("CLONES_DIR", "data/clones").strip() or "data/clones",
        wallet_pay_api_key=os.getenv("WALLET_PAY_API_KEY", "").strip(),
        wallet_pay_webhook_host=os.getenv("WALLET_PAY_WEBHOOK_HOST", "0.0.0.0").strip() or "0.0.0.0",
        wallet_pay_webhook_port=int(os.getenv("WALLET_PAY_WEBHOOK_PORT", "8765").strip() or "8765"),
        wallet_pay_webhook_path=os.getenv("WALLET_PAY_WEBHOOK_PATH", "/wallet-pay/webhook").strip()
        or "/wallet-pay/webhook",
        wallet_pay_return_url=os.getenv("WALLET_PAY_RETURN_URL", default_return).strip() or default_return,
        wallet_pay_order_timeout=int(os.getenv("WALLET_PAY_ORDER_TIMEOUT", "3600").strip() or "3600"),
        crypto_pay_api_token=os.getenv("CRYPTO_PAY_API_TOKEN", "").strip(),
        crypto_pay_testnet=os.getenv("CRYPTO_PAY_TESTNET", "0").strip() in ("1", "true", "yes"),
        crypto_pay_webhook_path=os.getenv("CRYPTO_PAY_WEBHOOK_PATH", "/crypto-pay/webhook").strip()
        or "/crypto-pay/webhook",
        crypto_pay_order_timeout=int(os.getenv("CRYPTO_PAY_ORDER_TIMEOUT", "3600").strip() or "3600"),
        crypto_pay_return_url=os.getenv("CRYPTO_PAY_RETURN_URL", default_return).strip() or default_return,
    )
