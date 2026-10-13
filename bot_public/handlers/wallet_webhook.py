"""Payment webhooks: Wallet Pay + Crypto Pay (@CryptoBot)."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web
from aiogram import Bot

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.services.child_manager import ChildManager
from bot_public.services.crypto_pay import PROVIDER_CRYPTOBOT, verify_cryptobot_signature
from bot_public.services.payment_fulfillment import fulfill_crypto_order
from bot_public.services.wallet_pay import verify_webhook_signature

logger = logging.getLogger(__name__)


def _webhook_paths(configured_path: str) -> tuple[str, ...]:
    path = configured_path.strip() or "/webhook"
    if not path.startswith("/"):
        path = f"/{path}"
    if path.endswith("/"):
        return path, path.rstrip("/")
    return path, f"{path}/"


async def handle_wallet_webhook(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    platform_db: PlatformDB = request.app["platform_db"]
    child_manager: ChildManager = request.app["child_manager"]
    config: Config = request.app["config"]

    if not config.wallet_pay_enabled:
        return web.Response(status=503, text="Wallet Pay not configured")

    body = await request.read()
    timestamp = request.headers.get("WalletPay-Timestamp", "")
    signature = request.headers.get("Walletpay-Signature", "")

    path_variants = _webhook_paths(config.wallet_pay_webhook_path)
    verified = any(
        verify_webhook_signature(
            method=request.method,
            path=path,
            timestamp=timestamp,
            body=body,
            signature=signature,
            api_key=config.wallet_pay_api_key,
        )
        for path in path_variants
    )
    if not verified:
        logger.warning("Wallet Pay webhook signature mismatch for %s", request.path)
        return web.Response(status=401, text="Invalid signature")

    try:
        messages: list[dict[str, Any]] = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    if not isinstance(messages, list):
        messages = [messages]

    for msg in messages:
        event_id = msg.get("eventId")
        if event_id is not None and await platform_db.is_wallet_event_processed(int(event_id)):
            continue

        msg_type = msg.get("type")
        payload = msg.get("payload") or {}
        external_id = payload.get("externalId")
        if not external_id:
            logger.warning("Wallet webhook without externalId: %s", msg)
            continue

        order = await platform_db.get_wallet_order(external_id)
        if not order:
            logger.warning("Wallet order not found: %s", external_id)
            if event_id is not None:
                await platform_db.mark_wallet_event_processed(int(event_id))
            continue

        if msg_type == "ORDER_PAID":
            try:
                await fulfill_crypto_order(
                    bot, platform_db, child_manager, config, order=order,
                )
            except Exception:
                logger.exception("Wallet fulfillment failed for %s", external_id)
                return web.Response(status=500, text="Fulfillment error")
        elif msg_type == "ORDER_FAILED":
            await platform_db.mark_wallet_order_failed(external_id)

        if event_id is not None:
            await platform_db.mark_wallet_event_processed(int(event_id))

    return web.Response(status=200, text="OK")


async def handle_cryptobot_webhook(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    platform_db: PlatformDB = request.app["platform_db"]
    child_manager: ChildManager = request.app["child_manager"]
    config: Config = request.app["config"]

    if not config.crypto_pay_enabled:
        return web.Response(status=503, text="Crypto Pay not configured")

    body = await request.read()
    signature = request.headers.get("crypto-pay-api-signature", "")
    if not verify_cryptobot_signature(
        api_token=config.crypto_pay_api_token,
        body=body,
        signature=signature,
    ):
        logger.warning("Crypto Pay webhook signature mismatch for %s", request.path)
        return web.Response(status=401, text="Invalid signature")

    try:
        data: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    update_id = data.get("update_id")
    if update_id is not None and await platform_db.is_cryptobot_event_processed(int(update_id)):
        return web.Response(status=200, text="OK")

    if data.get("update_type") != "invoice_paid":
        if update_id is not None:
            await platform_db.mark_cryptobot_event_processed(int(update_id))
        return web.Response(status=200, text="OK")

    invoice = data.get("payload") or {}
    invoice_id = invoice.get("invoice_id")
    if not invoice_id:
        logger.warning("Crypto Pay webhook without invoice_id: %s", data)
        return web.Response(status=400, text="Missing invoice_id")

    order = await platform_db.get_wallet_order_by_invoice(
        int(invoice_id), provider=PROVIDER_CRYPTOBOT,
    )
    if not order:
        external = invoice.get("payload")
        if external:
            order = await platform_db.get_wallet_order(str(external))
    if not order:
        logger.warning("Crypto Pay order not found for invoice %s", invoice_id)
        if update_id is not None:
            await platform_db.mark_cryptobot_event_processed(int(update_id))
        return web.Response(status=200, text="OK")

    try:
        await fulfill_crypto_order(
            bot, platform_db, child_manager, config, order=order,
        )
    except Exception:
        logger.exception("Crypto Pay fulfillment failed for invoice %s", invoice_id)
        return web.Response(status=500, text="Fulfillment error")

    if update_id is not None:
        await platform_db.mark_cryptobot_event_processed(int(update_id))
    return web.Response(status=200, text="OK")


async def start_payment_webhook_server(
    bot: Bot,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    config: Config,
) -> web.AppRunner | None:
    if not config.wallet_pay_enabled and not config.crypto_pay_enabled:
        logger.info("No payment webhooks configured")
        return None

    app = web.Application()
    app["bot"] = bot
    app["platform_db"] = platform_db
    app["child_manager"] = child_manager
    app["config"] = config

    if config.wallet_pay_enabled:
        for path in _webhook_paths(config.wallet_pay_webhook_path):
            app.router.add_post(path, handle_wallet_webhook)
    if config.crypto_pay_enabled:
        for path in _webhook_paths(config.crypto_pay_webhook_path):
            app.router.add_post(path, handle_cryptobot_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner,
        config.wallet_pay_webhook_host,
        config.wallet_pay_webhook_port,
    )
    await site.start()
    logger.info(
        "Payment webhooks on %s:%s (wallet=%s, cryptobot=%s)",
        config.wallet_pay_webhook_host,
        config.wallet_pay_webhook_port,
        "on" if config.wallet_pay_enabled else "off",
        "on" if config.crypto_pay_enabled else "off",
    )
    return runner


# Backward-compatible alias
start_wallet_webhook_server = start_payment_webhook_server
