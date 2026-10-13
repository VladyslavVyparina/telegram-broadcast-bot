"""Current subscription price/duration from admin settings (always read from DB)."""

from __future__ import annotations

from dataclasses import dataclass

from bot_public.database.db import PlatformDB
from bot_public.services.wallet_pay import parse_crypto_price
from bot_public.utils.crypto_prices import format_usdt_display


@dataclass(frozen=True)
class PaymentPlan:
    stars: int
    days: int
    usdt_display: str
    usdt_amount: str


async def load_payment_plan(platform_db: PlatformDB) -> PaymentPlan:
    usdt_raw = await platform_db.crypto_price_usdt()
    usdt_display = format_usdt_display(usdt_raw)
    _currency, usdt_amount = parse_crypto_price(usdt_raw)
    return PaymentPlan(
        stars=await platform_db.subscription_price(),
        days=await platform_db.subscription_days(),
        usdt_display=usdt_display,
        usdt_amount=usdt_amount,
    )
