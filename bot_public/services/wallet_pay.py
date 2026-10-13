"""Wallet Pay API client (https://docs.wallet.tg/pay/)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

API_BASE = "https://pay.wallet.tg/wpay/store-api/v1"
SUPPORTED_CURRENCIES = frozenset({"TON", "USDT", "BTC", "NOT"})
PRICE_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(USDT|TON|BTC|NOT)\s*$",
    re.IGNORECASE,
)
BARE_AMOUNT_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*$")


@dataclass(frozen=True)
class WalletOrderResult:
    order_id: int
    external_id: str
    direct_pay_link: str
    currency: str
    amount: str


class WalletPayError(Exception):
    pass


def parse_crypto_price(text: str) -> tuple[str, str]:
    raw = text.strip()
    bare = BARE_AMOUNT_RE.match(raw)
    if bare:
        return "USDT", bare.group(1).replace(",", ".")
    match = PRICE_RE.match(raw)
    if not match:
        raise WalletPayError(f"Invalid crypto price format: {text!r}")
    amount = match.group(1).replace(",", ".")
    currency = match.group(2).upper()
    return currency, amount


def make_external_id(prefix: str, user_id: int) -> str:
    return f"{prefix}-{user_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"


def verify_webhook_signature(
    *,
    method: str,
    path: str,
    timestamp: str,
    body: bytes,
    signature: str,
    api_key: str,
) -> bool:
    body_b64 = base64.b64encode(body).decode("ascii")
    message = f"{method}.{path}.{timestamp}.{body_b64}"
    digest = hmac.new(api_key.encode(), message.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


async def create_order(
    api_key: str,
    *,
    currency: str,
    amount: str,
    description: str,
    external_id: str,
    customer_telegram_user_id: int,
    return_url: str,
    fail_return_url: str,
    custom_data: str,
    timeout_seconds: int = 3600,
) -> WalletOrderResult:
    currency = currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise WalletPayError(f"Unsupported currency: {currency}")

    payload: dict[str, Any] = {
        "amount": {
            "currencyCode": currency,
            "amount": amount,
        },
        "autoConversionCurrency": currency,
        "description": description[:100],
        "externalId": external_id[:255],
        "timeoutSeconds": max(30, min(timeout_seconds, 864000)),
        "customerTelegramUserId": customer_telegram_user_id,
        "returnUrl": return_url,
        "failReturnUrl": fail_return_url,
        "customData": custom_data[:255],
    }

    headers = {
        "Wpay-Store-Api-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE}/order",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            raw = await resp.text()
            if resp.status != 200:
                logger.error("Wallet Pay create_order HTTP %s: %s", resp.status, raw)
                raise WalletPayError(f"Wallet Pay API error HTTP {resp.status}")

            data = json.loads(raw)
            if data.get("status") != "SUCCESS":
                raise WalletPayError(data.get("message") or "Wallet Pay order failed")

            order = data["data"]
            link = order.get("directPayLink") or order.get("payLink")
            if not link:
                raise WalletPayError("Wallet Pay response missing payment link")

            return WalletOrderResult(
                order_id=int(order["id"]),
                external_id=external_id,
                direct_pay_link=link,
                currency=currency,
                amount=amount,
            )


async def get_order_status(api_key: str, order_id: int) -> str:
    """Return Wallet Pay order status: ACTIVE, PAID, EXPIRED, CANCELLED, …"""
    headers = {
        "Wpay-Store-Api-Key": api_key,
        "Accept": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_BASE}/order/preview",
            headers=headers,
            params={"id": str(order_id)},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            raw = await resp.text()
            if resp.status != 200:
                logger.warning("Wallet Pay preview HTTP %s: %s", resp.status, raw)
                raise WalletPayError(f"Wallet Pay preview HTTP {resp.status}")
            data = json.loads(raw)
            if data.get("status") != "SUCCESS":
                raise WalletPayError(data.get("message") or "Wallet Pay preview failed")
            return str(data["data"].get("status", "")).upper()


def encode_custom_data(**fields: Any) -> str:
    return json.dumps(fields, separators=(",", ":"), ensure_ascii=True)


def decode_custom_data(raw: str | None) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
