"""Backward-compatible alias for payment fulfillment."""

from bot_public.services.payment_fulfillment import fulfill_crypto_order as fulfill_wallet_order

__all__ = ["fulfill_wallet_order"]
