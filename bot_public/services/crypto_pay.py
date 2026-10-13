"""Crypto Pay API client (@CryptoBot — https://help.crypt.bot/crypto-pay-api)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp

from bot_public.services.wallet_pay import WalletPayError, parse_crypto_price

logger = logging.getLogger(__name__)

PROVIDER_CRYPTOBOT = "cryptobot"
SUPPORTED_ASSETS = frozenset({"USDT", "TON", "BTC", "ETH", "LTC", "TRX", "USDC", "BNB"})


@dataclass(frozen=True)
class CryptoInvoiceResult:
    invoice_id: int
    external_id: str
    pay_url: str
    asset: str
    amount: str


class CryptoPayError(Exception):
    pass


def api_base_url(*, testnet: bool) -> str:
    host = "testnet-pay.crypt.bot" if testnet else "pay.crypt.bot"
    return f"https://{host}/api"


def make_external_id(prefix: str, user_id: int) -> str:
    return f"{prefix}-{user_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"


def verify_cryptobot_signature(
    *,
    api_token: str,
    body: bytes,
    signature: str,
) -> bool:
    if not signature:
        return False
    secret = hashlib.sha256(api_token.encode()).digest()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        return True
    try:
        parsed = json.loads(body)
        for variant in (
            json.dumps(parsed, separators=(",", ":"), ensure_ascii=False),
            json.dumps(parsed, separators=(",", ":"), ensure_ascii=True),
        ):
            alt = hmac.new(secret, variant.encode("utf-8"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(alt, signature):
                return True
    except json.JSONDecodeError:
        pass
    return False


async def _api_request(
    method: str,
    api_token: str,
    params: dict[str, Any],
    *,
    testnet: bool,
) -> dict[str, Any]:
    url = f"{api_base_url(testnet=testnet)}/{method}"
    headers = {"Crypto-Pay-API-Token": api_token, "Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers=headers,
            params=params,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            raw = await resp.text()
            if resp.status != 200:
                logger.error("Crypto Pay %s HTTP %s: %s", method, resp.status, raw)
                raise CryptoPayError(f"Crypto Pay HTTP {resp.status}")
            data = json.loads(raw)
            if not data.get("ok"):
                err = data.get("error")
                if isinstance(err, dict):
                    msg = err.get("name") or str(err)
                else:
                    msg = str(err) if err else "Crypto Pay API error"
                raise CryptoPayError(msg)
            result = data.get("result")
            if result is None:
                raise CryptoPayError("Crypto Pay response missing result")
            return result


async def create_invoice(
    api_token: str,
    *,
    asset: str,
    amount: str,
    description: str,
    payload: str,
    return_url: str,
    external_id: str,
    expires_in: int = 3600,
    testnet: bool = False,
) -> CryptoInvoiceResult:
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise CryptoPayError(f"Unsupported asset: {asset}")

    result = await _api_request(
        "createInvoice",
        api_token,
        {
            "asset": asset,
            "amount": amount,
            "description": description[:1024],
            "payload": payload[:4096],
            "paid_btn_name": "openBot",
            "paid_btn_url": return_url,
            "expires_in": max(1, min(expires_in, 2678400)),
            "allow_comments": "false",
            "allow_anonymous": "true",
        },
        testnet=testnet,
    )

    if isinstance(result, list):
        if not result:
            raise CryptoPayError("Crypto Pay createInvoice returned empty list")
        invoice = result[0]
    else:
        invoice = result

    pay_url = (
        invoice.get("bot_invoice_url")
        or invoice.get("mini_app_invoice_url")
        or invoice.get("pay_url")
        or invoice.get("web_app_invoice_url")
    )
    if not pay_url:
        raise CryptoPayError("Crypto Pay response missing payment URL")

    return CryptoInvoiceResult(
        invoice_id=int(invoice["invoice_id"]),
        external_id=external_id,
        pay_url=pay_url,
        asset=asset,
        amount=amount,
    )


async def get_invoice_status(
    api_token: str,
    invoice_id: int,
    *,
    testnet: bool = False,
) -> str:
    result = await _api_request(
        "getInvoices",
        api_token,
        {"invoice_ids": str(invoice_id)},
        testnet=testnet,
    )
    items = result if isinstance(result, list) else result.get("items") or []
    if not items:
        raise CryptoPayError(f"Invoice {invoice_id} not found")
    return str(items[0].get("status", "")).lower()


def parse_price_for_asset(price_text: str) -> tuple[str, str]:
    """Parse admin price like '20 USDT' -> ('USDT', '20')."""
    try:
        return parse_crypto_price(price_text)
    except WalletPayError as exc:
        raise CryptoPayError(str(exc)) from exc


def encode_payload(**fields: Any) -> str:
    return json.dumps(fields, separators=(",", ":"), ensure_ascii=True)
