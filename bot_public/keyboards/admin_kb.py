from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot_public.locales import t

BOTS_PER_PAGE = 6


def admin_hub_kb(lang: str, *, paid_mode: bool) -> InlineKeyboardMarkup:
    mode_btn = (
        t(lang, "admin_btn_free_on") if not paid_mode else t(lang, "admin_btn_paid_on")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "admin_section_features"),
                callback_data="admin:section:features",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_section_billing"),
                callback_data="admin:section:billing",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_section_ops"),
                callback_data="admin:section:ops",
            )],
            [InlineKeyboardButton(text=mode_btn, callback_data="admin:toggle_paid")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:main")],
        ]
    )


def admin_features_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="admin:panel"),
        ]]
    )


def admin_billing_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_stars_price"),
                callback_data="admin:price",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_usdt_price"),
                callback_data="admin:crypto_price_usdt",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_duration"),
                callback_data="admin:duration",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_grant"),
                callback_data="admin:grant",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_stars_balance"),
                callback_data="admin:stars",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_purchases"),
                callback_data="admin:purchases",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="admin:panel")],
        ]
    )


def admin_ops_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_network_stats"),
                callback_data="admin:ops:stats",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_manage_bots"),
                callback_data="admin:ops:bots:0",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_all"),
                callback_data="admin:ops:bc:all",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_private"),
                callback_data="admin:ops:bc:private",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_groups"),
                callback_data="admin:ops:bc:groups",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_one_bot"),
                callback_data="admin:ops:bc:pick:0",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_auto_reply"),
                callback_data="admin:ops:auto_reply",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_start_all"),
                callback_data="admin:ops:start_all",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_stop_all"),
                callback_data="admin:ops:stop_all",
            )],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="admin:panel")],
        ]
    )


def admin_bots_kb(
    lang: str,
    bots: list[dict],
    *,
    page: int,
    running_ids: set[int],
) -> InlineKeyboardMarkup:
    start = page * BOTS_PER_PAGE
    chunk = bots[start:start + BOTS_PER_PAGE]
    rows: list[list[InlineKeyboardButton]] = []

    for bot in chunk:
        bot_id = int(bot["id"])
        username = bot.get("bot_username") or f"id{bot_id}"
        disabled = bool(bot.get("is_disabled"))
        running = bot_id in running_ids and not disabled
        if disabled:
            icon = "⛔"
        elif running:
            icon = "🟢"
        else:
            icon = "🔴"
        rows.append([InlineKeyboardButton(
            text=f"{icon} @{username}",
            callback_data=f"admin:bot:{bot_id}",
        )])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️", callback_data=f"admin:ops:bots:{page - 1}",
        ))
    if start + BOTS_PER_PAGE < len(bots):
        nav.append(InlineKeyboardButton(
            text="▶️", callback_data=f"admin:ops:bots:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="admin:section:ops",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_bot_detail_kb(lang: str, bot_id: int, *, disabled: bool, running: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if disabled:
        rows.append([InlineKeyboardButton(
            text=t(lang, "admin_btn_enable_bot"),
            callback_data=f"admin:bot:start:{bot_id}",
        )])
    else:
        rows.append([InlineKeyboardButton(
            text=t(lang, "admin_btn_disable_bot"),
            callback_data=f"admin:bot:stop:{bot_id}",
        )])
        if running:
            rows.append([InlineKeyboardButton(
                text=t(lang, "admin_btn_restart_bot"),
                callback_data=f"admin:bot:restart:{bot_id}",
            )])
        else:
            rows.append([InlineKeyboardButton(
                text=t(lang, "admin_btn_start_bot"),
                callback_data=f"admin:bot:start:{bot_id}",
            )])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="admin:ops:bots:0",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_auto_reply_kb(lang: str, items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, item in enumerate(items[:10]):
        trigger = item.get("trigger", "?")
        preview = (item.get("reply_text") or "")[:28]
        if len(item.get("reply_text") or "") > 28:
            preview += "…"
        rows.append([InlineKeyboardButton(
            text=f"✏️ {trigger} → {preview}",
            callback_data=f"admin:ar:i:{idx}",
        )])
    rows.append([InlineKeyboardButton(
        text=t(lang, "admin_btn_ar_add"),
        callback_data="admin:ops:ar:add",
    )])
    if items:
        rows.append([InlineKeyboardButton(
            text=t(lang, "admin_btn_ar_sync"),
            callback_data="admin:ops:ar:sync",
        )])
        rows.append([InlineKeyboardButton(
            text=t(lang, "admin_btn_ar_clear"),
            callback_data="admin:ops:ar:clear",
        )])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="admin:section:ops",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_ar_item_kb(lang: str, index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_ar_edit_reply"),
                callback_data=f"admin:ar:edit_reply:{index}",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_ar_edit_trigger"),
                callback_data=f"admin:ar:edit_trigger:{index}",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_ar_delete"),
                callback_data=f"admin:ar:del:{index}",
            )],
            [InlineKeyboardButton(
                text=t(lang, "btn_back"), callback_data="admin:ops:auto_reply",
            )],
        ]
    )


def admin_bc_pick_bot_kb(
    lang: str,
    bots: list[dict],
    *,
    page: int,
) -> InlineKeyboardMarkup:
    start = page * BOTS_PER_PAGE
    chunk = bots[start:start + BOTS_PER_PAGE]
    rows: list[list[InlineKeyboardButton]] = []
    for bot in chunk:
        bot_id = int(bot["id"])
        username = bot.get("bot_username") or f"id{bot_id}"
        rows.append([InlineKeyboardButton(
            text=f"📢 @{username}",
            callback_data=f"admin:ops:bc:sel:{bot_id}",
        )])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️", callback_data=f"admin:ops:bc:pick:{page - 1}",
        ))
    if start + BOTS_PER_PAGE < len(bots):
        nav.append(InlineKeyboardButton(
            text="▶️", callback_data=f"admin:ops:bc:pick:{page + 1}",
        ))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="admin:section:ops",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_bc_audience_kb(lang: str, bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_all"),
                callback_data=f"admin:ops:bc:bot:{bot_id}:all",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_private"),
                callback_data=f"admin:ops:bc:bot:{bot_id}:private",
            )],
            [InlineKeyboardButton(
                text=t(lang, "admin_btn_broadcast_groups"),
                callback_data=f"admin:ops:bc:bot:{bot_id}:groups",
            )],
            [InlineKeyboardButton(
                text=t(lang, "btn_back"), callback_data="admin:ops:bc:pick:0",
            )],
        ]
    )
