from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.menus import finance_kb
from bot.locales import t
from bot.services.paid_access import (
    get_subscription_days,
    get_subscription_period,
    get_subscription_status_text,
    paywall_kb,
)
from bot.utils.helpers import format_display_time
from bot.utils.states import FinanceState
from bot.utils.subscription import days_to_months, format_months_label, months_to_days

router = Router()
admin = AdminFilter()


def _fin_back_kb(lang: str) -> InlineKeyboardMarkup:
    from bot.keyboards.inline import back_button

    return InlineKeyboardMarkup(inline_keyboard=[[back_button(lang, "menu:finance")]])


# ── Admin finance menus ───────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "fin:store")
async def fin_store(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    products = await db.get_finance_products()
    lines = [f"<b>{t(lang, 'fin_store')}</b>", "━━━━━━━━━━━━━━━━"]
    rows = []
    for p in products:
        lines.append(f"• {p['title']} — {p['price_stars']}⭐")
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 {p['title'][:20]}",
                callback_data=f"fin:delprod:{p['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t(lang, "fin_add_product"), callback_data="fin:addprod")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:finance")])
    if not products:
        lines.append(t(lang, "fin_store_empty"))
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "fin:addprod")
async def fin_add_product(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_product_title)
    await callback.message.edit_text(t(lang, "fin_product_title_prompt"))
    await callback.answer()


@router.message(admin, FinanceState.waiting_product_title)
async def fin_product_title(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(FinanceState.waiting_product_desc)
    await message.answer(t(lang, "fin_product_desc_prompt"))


@router.message(admin, FinanceState.waiting_product_desc)
async def fin_product_desc(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.update_data(description=message.text.strip() if message.text else "")
    await state.set_state(FinanceState.waiting_product_price)
    await message.answer(t(lang, "fin_product_price_prompt"))


@router.message(admin, FinanceState.waiting_product_price)
async def fin_product_price(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text or not message.text.strip().isdigit():
        await message.answer(t(lang, "fin_product_price_prompt"))
        return
    data = await state.get_data()
    await state.clear()
    price = int(message.text.strip())
    pid = await db.add_finance_product(data["title"], data.get("description", ""), price)
    await db.log_activity("add_product", f"{pid}:{data['title']}", config.admin_id)
    await message.answer(t(lang, "fin_product_added", title=data["title"]))


@router.callback_query(admin, F.data.startswith("fin:delprod:"))
async def fin_del_product(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    pid = int(callback.data.split(":")[-1])
    await db.delete_finance_product(pid)
    await callback.answer(t(lang, "fin_product_deleted"))
    await fin_store(callback, db, config)


@router.callback_query(admin, F.data == "fin:donations")
async def fin_donations(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    amount = await db.get_cfg("finance_donation_amount", "10")
    enabled = await db.get_cfg_bool("finance_donations_enabled")
    status = "✅" if enabled else "❌"
    text = (
        f"<b>{t(lang, 'fin_donations')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{status} {t(lang, 'fin_donation_amount', amount=amount)}\n"
        f"{t(lang, 'fin_donation_hint')}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "fin_toggle_donations"),
                callback_data="fin:toggledon",
            )],
            [InlineKeyboardButton(
                text=t(lang, "fin_set_donation"),
                callback_data="fin:setdon",
            )],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:finance")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(admin, F.data == "fin:toggledon")
async def fin_toggle_donations(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("finance_donations_enabled")
    await fin_donations(callback, db, config)


@router.callback_query(admin, F.data == "fin:setdon")
async def fin_set_donation(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_donation_amount)
    await callback.message.edit_text(t(lang, "fin_donation_set_prompt"))
    await callback.answer()


@router.message(admin, FinanceState.waiting_donation_amount)
async def fin_donation_amount(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text or not message.text.strip().isdigit():
        return
    await state.clear()
    await db.set_cfg("finance_donation_amount", message.text.strip())
    await message.answer(t(lang, "setting_saved"))


@router.callback_query(admin, F.data == "fin:access")
async def fin_access(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    price, months, months_label = await get_subscription_period(db)
    enabled = await db.get_cfg_bool("finance_access_enabled")
    status = "✅" if enabled else "❌"
    subs = await db.count_paid_subscribers()
    text = (
        f"<b>{t(lang, 'fin_access')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{status} {t(lang, 'fin_access_info', price=price, months_label=months_label)}\n"
        f"{t(lang, 'fin_access_subs', count=subs)}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "fin_toggle_access"), callback_data="fin:toggleacc")],
            [InlineKeyboardButton(text=t(lang, "fin_set_access"), callback_data="fin:setacc")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:finance")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(admin, F.data == "fin:toggleacc")
async def fin_toggle_access(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("finance_access_enabled")
    await fin_access(callback, db, config)


@router.callback_query(admin, F.data == "fin:setacc")
async def fin_set_access(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_access_price)
    await callback.message.edit_text(t(lang, "fin_access_set_prompt"))
    await callback.answer()


@router.message(admin, FinanceState.waiting_access_price)
async def fin_access_price(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    parts = message.text.strip().split()
    if not parts[0].isdigit():
        return
    await state.clear()
    price = parts[0]
    months = parts[1] if len(parts) > 1 and parts[1].isdigit() else "1"
    await db.set_cfg("finance_access_price", price)
    await db.set_cfg("finance_access_months", months)
    await db.set_cfg("finance_access_days", str(months_to_days(int(months))))
    months_label = format_months_label(int(months), lang)
    await message.answer(
        t(lang, "fin_access_saved", price=price, months_label=months_label)
    )


@router.callback_query(admin, F.data == "fin:settings")
async def fin_settings(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:finance")],
        ]
    )
    await callback.message.edit_text(
        f"<b>{t(lang, 'fin_settings')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'fin_settings_info')}",
        reply_markup=kb,
    )
    await callback.answer()


# ── User payments (Telegram Stars) ────────────────────────────────────────────

@router.message(F.text == "/shop")
async def user_shop(message: Message, db: Database, config: Config) -> None:
    if not message.from_user:
        return
    lang = config.default_language
    products = await db.get_finance_products()
    if not products:
        await message.answer(t(lang, "fin_store_empty"))
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(
            text=f"{p['title']} — {p['price_stars']}⭐",
            callback_data=f"fin:buy:{p['id']}",
        )]
        for p in products
    ]
    await message.answer(t(lang, "fin_store"), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.message(F.text == "/donate")
async def user_donate_cmd(message: Message, db: Database, config: Config) -> None:
    if not message.from_user:
        return
    lang = config.default_language
    if not await db.get_cfg_bool("finance_donations_enabled"):
        await message.answer(t(lang, "fin_coming"))
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    await message.answer(
        t(lang, "fin_donations"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❤️ Donate", callback_data="fin:donate")]]
        ),
    )


@router.message(F.text.in_({"/premium", "/status", "/subscription"}))
async def user_premium(message: Message, db: Database, config: Config) -> None:
    if not message.from_user:
        return
    lang = config.default_language
    if not await db.get_cfg_bool("finance_access_enabled"):
        await message.answer(t(lang, "fin_coming"))
        return

    uid = message.from_user.id
    text = await get_subscription_status_text(db, uid, lang, config.timezone)
    rows = []
    if await db.has_paid_access(uid):
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "paid_access_renew_btn"),
                callback_data="fin:buyaccess",
            )
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "paid_access_buy_btn"),
                callback_data="fin:buyaccess",
            )
        ])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "fin:status")
async def fin_status_callback(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    lang = config.default_language
    if not await db.get_cfg_bool("finance_access_enabled"):
        await callback.answer(t(lang, "fin_coming"), show_alert=True)
        return
    text = await get_subscription_status_text(
        db, callback.from_user.id, lang, config.timezone
    )
    await callback.message.answer(text, reply_markup=paywall_kb(lang, show_status=False))
    await callback.answer()


@router.callback_query(F.data.startswith("fin:buy:"))
async def fin_buy_product(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    pid = int(callback.data.split(":")[-1])
    product = await db.get_finance_product(pid)
    if not product:
        await callback.answer()
        return
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["title"],
        description=product.get("description") or product["title"],
        payload=f"product:{pid}",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=int(product["price_stars"]))],
    )
    await callback.answer()


@router.callback_query(F.data == "fin:donate")
async def fin_donate_user(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    if not await db.get_cfg_bool("finance_donations_enabled"):
        await callback.answer()
        return
    amount = int(await db.get_cfg("finance_donation_amount", "10"))
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Donation",
        description="Support the bot",
        payload="donation",
        currency="XTR",
        prices=[LabeledPrice(label="Donation", amount=amount)],
    )
    await callback.answer()


@router.callback_query(F.data == "fin:buyaccess")
async def fin_buy_access(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    if not await db.get_cfg_bool("finance_access_enabled"):
        await callback.answer()
        return
    price = int(await db.get_cfg("finance_access_price", "100"))
    days = await get_subscription_days(db)
    lang = config.default_language
    months_label = format_months_label(days_to_months(days), lang)
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "fin_access_invoice_title"),
        description=t(lang, "fin_access_invoice_desc", months_label=months_label),
        payload=f"access:{days}",
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, "fin_access_invoice_title"), amount=price)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not message.successful_payment:
        return
    payment = message.successful_payment
    payload = payment.invoice_payload
    amount = payment.total_amount
    uid = message.from_user.id

    if payload.startswith("product:"):
        pid = int(payload.split(":")[1])
        await db.record_finance_order(uid, amount, "product", product_id=pid, payload=payload)
    elif payload.startswith("access:"):
        days = int(payload.split(":")[1])
        await db.record_finance_order(uid, amount, "access", payload=payload)
        expires = await db.grant_access(uid, days=days)
    else:
        await db.record_finance_order(uid, amount, "donation", payload=payload)

    lang = config.default_language
    if payload.startswith("access:"):
        date_str = format_display_time(expires, config.timezone)
        await message.answer(t(lang, "fin_payment_success_until", date=date_str))
    else:
        await message.answer(t(lang, "fin_payment_success"))
