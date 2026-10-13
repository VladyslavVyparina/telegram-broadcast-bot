"""USDT price formatting for admin settings and payment UI."""

from __future__ import annotations

from bot_public.services.wallet_pay import WalletPayError, parse_crypto_price


def normalize_usdt_price(text: str) -> str:
    """Accept '25', '25 USDT', etc. and return '25 USDT'."""
    currency, amount = parse_crypto_price(text.strip())
    if currency != "USDT":
        raise WalletPayError(f"Expected USDT price, got {currency}")
    return f"{amount} USDT"


def format_usdt_display(text: str) -> str:
    return normalize_usdt_price(text)
