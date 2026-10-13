from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot_public.locales import t


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang:ar"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


def main_kb(lang: str, *, show_admin: bool = False, paid_mode: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=t(lang, "btn_create_free" if not paid_mode else "btn_create"),
            callback_data="create:intro",
        )],
        [InlineKeyboardButton(text=t(lang, "btn_my_bots"), callback_data="my:bots")],
        [InlineKeyboardButton(text=t(lang, "btn_language"), callback_data="lang:menu")],
    ]
    if show_admin:
        rows.append([
            InlineKeyboardButton(text=t(lang, "btn_admin"), callback_data="admin:panel")
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb(lang: str, callback: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=callback)
        ]]
    )


def pay_methods_kb(lang: str, stars: int, *, usdt_price: str, days: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_pay_stars", price=stars),
                callback_data="pay:method:stars",
            )],
            [InlineKeyboardButton(
                text=t(lang, "btn_pay_crypto", price=usdt_price, days=days),
                callback_data="pay:method:crypto",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:main")],
        ]
    )


def crypto_pay_kb(lang: str, *, usdt_price: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_cryptobot_usdt", price=usdt_price),
                callback_data="pay:cryptobot:usdt",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="create:intro")],
        ]
    )


def crypto_pay_link_kb(lang: str, pay_url: str, *, price: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_cryptobot_pay", price=price),
                url=pay_url,
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="pay:method:crypto")],
        ]
    )


def wallet_pay_kb(lang: str, *, usdt_price: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_wallet_usdt", price=usdt_price),
                callback_data="pay:wallet:usdt",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="create:intro")],
        ]
    )


def wallet_pay_link_kb(lang: str, pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_wallet_pay"),
                url=pay_url,
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="pay:method:crypto")],
        ]
    )


def crypto_wallets_kb(
    lang: str, admin_username: str, *, usdt_price: str,
) -> InlineKeyboardMarkup:
    admin = (admin_username or "sftsfdrtghbot").strip().lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "btn_crypto_trc20", price=usdt_price),
                callback_data="pay:crypto:trc20",
            )],
            [InlineKeyboardButton(
                text=t(lang, "btn_crypto_admin", admin=admin),
                url=f"https://t.me/{admin}",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="create:intro")],
        ]
    )


def renew_kb(lang: str, bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "btn_renew"),
                callback_data=f"renew:{bot_id}",
            )
        ]]
    )


def bot_renew_kb(lang: str, bot_id: int) -> InlineKeyboardMarkup:
    return renew_kb(lang, bot_id)
