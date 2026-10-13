from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.layout import row, rows_smart
from bot.locales import t
from bot.utils.toggle import toggle_btn


def back_button(lang: str, callback: str = "menu:main") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, "back"), callback_data=callback)


def sep_button(lang: str, key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, key), callback_data="noop")


# ── Main menu (2 columns, like reference) ─────────────────────────────────────

def main_menu_kb(
    lang: str,
    notify_join: bool = True,
    notify_ban: bool = True,
    *,
    show_finance: bool = False,
) -> InlineKeyboardMarkup:
    nj = toggle_btn(t(lang, "notify_join_label"), notify_join, suffix=True)
    nb = toggle_btn(t(lang, "notify_ban_label"), notify_ban, suffix=True)
    rows: list[list[InlineKeyboardButton]] = [
        row(
            InlineKeyboardButton(text=t(lang, "menu_content"), callback_data="menu:content"),
            InlineKeyboardButton(text=t(lang, "menu_settings"), callback_data="menu:settings"),
        ),
        row(
            InlineKeyboardButton(text=t(lang, "menu_subscription"), callback_data="menu:subscription"),
            InlineKeyboardButton(text=t(lang, "menu_users"), callback_data="menu:users"),
        ),
    ]
    if show_finance:
        rows.append(row(
            InlineKeyboardButton(text=t(lang, "menu_finance"), callback_data="menu:finance"),
            InlineKeyboardButton(text=t(lang, "menu_communication"), callback_data="menu:communication"),
        ))
        rows.append([InlineKeyboardButton(text=t(lang, "menu_autopost"), callback_data="menu:autopost")])
        rows.append([InlineKeyboardButton(text=t(lang, "menu_system"), callback_data="menu:system")])
    else:
        rows.append(row(
            InlineKeyboardButton(text=t(lang, "menu_communication"), callback_data="menu:communication"),
            InlineKeyboardButton(text=t(lang, "menu_autopost"), callback_data="menu:autopost"),
        ))
        rows.append([InlineKeyboardButton(text=t(lang, "menu_system"), callback_data="menu:system")])
    rows.append(row(
        InlineKeyboardButton(text=nb, callback_data="toggle:notify_ban"),
        InlineKeyboardButton(text=nj, callback_data="toggle:notify_join"),
    ))
    rows.append([InlineKeyboardButton(text=t(lang, "menu_guide"), callback_data="menu:guide")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Settings ──────────────────────────────────────────────────────────────────

def settings_main_kb(lang: str, cfg: dict) -> InlineKeyboardMarkup:
    ad_on = cfg.get("auto_delete_enabled") == "1"
    in_on = cfg.get("inactive_enabled") == "1"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "set_bot_work"), callback_data="set:botwork")],
            [InlineKeyboardButton(text=t(lang, "set_verification"), callback_data="set:verify")],
            [InlineKeyboardButton(text=t(lang, "set_content_protect"), callback_data="set:protect")],
            [InlineKeyboardButton(text=t(lang, "set_notifications"), callback_data="set:notifs")],
            [InlineKeyboardButton(
                text=toggle_btn(t(lang, "set_auto_delete"), ad_on, use_dot=True),
                callback_data="set:autodel",
            )],
            [InlineKeyboardButton(
                text=toggle_btn(t(lang, "set_inactive"), in_on, use_dot=True),
                callback_data="set:inactive",
            )],
            [InlineKeyboardButton(
                text=t(lang, "set_quick_replies", count="{count}"),
                callback_data="set:qreplies",
            )],
            [InlineKeyboardButton(text=t(lang, "set_language_menu"), callback_data="set:langmenu")],
            [back_button(lang)],
        ]
    )


def settings_main_kb_with_count(lang: str, cfg: dict, qr_count: int) -> InlineKeyboardMarkup:
    ad_on = cfg.get("auto_delete_enabled") == "1"
    in_on = cfg.get("inactive_enabled") == "1"
    return InlineKeyboardMarkup(
        inline_keyboard=rows_smart(
            InlineKeyboardButton(text=t(lang, "set_bot_work"), callback_data="set:botwork"),
            InlineKeyboardButton(text=t(lang, "set_verification"), callback_data="set:verify"),
            InlineKeyboardButton(text=t(lang, "set_content_protect"), callback_data="set:protect"),
            InlineKeyboardButton(text=t(lang, "set_notifications"), callback_data="set:notifs"),
            InlineKeyboardButton(
                text=toggle_btn(t(lang, "set_auto_delete"), ad_on, use_dot=True, suffix=True),
                callback_data="set:autodel",
            ),
            InlineKeyboardButton(
                text=toggle_btn(t(lang, "set_inactive"), in_on, use_dot=True, suffix=True),
                callback_data="set:inactive",
            ),
            InlineKeyboardButton(
                text=t(lang, "set_quick_replies").format(count=qr_count),
                callback_data="set:qreplies",
            ),
            InlineKeyboardButton(text=t(lang, "set_language_menu"), callback_data="set:langmenu"),
            back_button(lang),
        )
    )


def bot_work_kb(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=toggle_btn(t(lang, "bot_work_toggle"), enabled, use_dot=True),
                callback_data="set:botwork:toggle",
            )],
            [back_button(lang, "menu:settings")],
        ]
    )


def content_protect_kb(lang: str, cfg: dict) -> InlineKeyboardMarkup:
    prot = cfg.get("content_protection") == "1"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:protect:help")],
            *rows_smart(
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "protect_bot_content"), prot, suffix=True),
                    callback_data="set:protect:toggle",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "protect_exclude_media"), cfg.get("content_exclude_media") == "1", suffix=True),
                    callback_data="set:protect:media",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "protect_exclude_links"), cfg.get("content_exclude_links") == "1", suffix=True),
                    callback_data="set:protect:links",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "protect_exclude_text"), cfg.get("content_exclude_text") == "1", suffix=True),
                    callback_data="set:protect:text",
                ),
            ),
            [back_button(lang, "menu:settings")],
        ]
    )


def notifications_kb(lang: str, join: bool, ban: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:notifs:help")],
            row(
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "notify_join_label"), join, suffix=True),
                    callback_data="set:notifs:join",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "notify_ban_label"), ban, suffix=True),
                    callback_data="set:notifs:ban",
                ),
            ),
            [back_button(lang, "menu:settings")],
        ]
    )


def verification_kb(lang: str, mode: str) -> InlineKeyboardMarkup:
    modes = [
        ("disabled", "verify_disabled"),
        ("captcha", "verify_captcha"),
        ("website", "verify_website"),
        ("phone", "verify_phone"),
        ("invitation", "verify_invitation"),
        ("approval", "verify_approval"),
    ]
    mode_buttons = []
    for m, label_key in modes:
        mark = "✅ " if mode == m else ""
        mode_buttons.append(InlineKeyboardButton(
            text=f"{mark}{t(lang, label_key)}",
            callback_data=f"set:verify:mode:{m}",
        ))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(*mode_buttons),
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:verify:help")],
            [InlineKeyboardButton(text=t(lang, "verify_config_btn"), callback_data="set:verify:config")],
            [back_button(lang, "menu:settings")],
        ]
    )


def auto_delete_kb(lang: str, cfg: dict) -> InlineKeyboardMarkup:
    on = cfg.get("auto_delete_enabled") == "1"
    mins = cfg.get("auto_delete_minutes", "5")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_enable"), on, use_dot=True, suffix=True),
                    callback_data="set:ad:toggle",
                ),
                InlineKeyboardButton(
                    text=t(lang, "ad_duration", minutes=mins),
                    callback_data="set:ad:duration",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(f"{t(lang, 'ad_private')} 💬", cfg.get("auto_delete_private") == "1", suffix=True),
                    callback_data="set:ad:private",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(f"{t(lang, 'ad_groups')} 👥", cfg.get("auto_delete_groups") == "1", suffix=True),
                    callback_data="set:ad:groups",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(f"{t(lang, 'ad_channels')} 📢", cfg.get("auto_delete_channels") == "1", suffix=True),
                    callback_data="set:ad:channels",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_user_msgs"), cfg.get("auto_delete_user_msgs") == "1", suffix=True),
                    callback_data="set:ad:usermsgs",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_between"), cfg.get("auto_delete_between") == "1", suffix=True),
                    callback_data="set:ad:between",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_reaction"), cfg.get("auto_delete_reaction") == "1", suffix=True),
                    callback_data="set:ad:reaction",
                ),
            ),
            [sep_button(lang, "ad_exceptions_sep")],
            *rows_smart(
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_ex_start"), cfg.get("auto_delete_ex_start") == "1", suffix=True),
                    callback_data="set:ad:exstart",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_ex_buttons"), cfg.get("auto_delete_ex_buttons") == "1", suffix=True),
                    callback_data="set:ad:exbuttons",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_ex_payment"), cfg.get("auto_delete_ex_payment") == "1", suffix=True),
                    callback_data="set:ad:expayment",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "ad_ex_admin"), cfg.get("auto_delete_ex_admin") == "1", suffix=True),
                    callback_data="set:ad:exadmin",
                ),
            ),
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:ad:help")],
            [back_button(lang, "menu:settings")],
        ]
    )


def auto_delete_duration_kb(lang: str) -> InlineKeyboardMarkup:
    options = [1, 3, 5, 10, 15, 30, 60]
    rows = []
    for i in range(0, len(options), 2):
        pair = []
        for m in options[i : i + 2]:
            pair.append(InlineKeyboardButton(
                text=f"⏱️ {m} {t(lang, 'minutes')}",
                callback_data=f"set:ad:mins:{m}",
            ))
        rows.append(pair)
    rows.append([back_button(lang, "set:autodel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inactive_kb(lang: str, cfg: dict, reminders_count: int) -> InlineKeyboardMarkup:
    on = cfg.get("inactive_enabled") == "1"
    hours = f"{cfg.get('inactive_hours_start', '0')}-{cfg.get('inactive_hours_end', '24')}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=toggle_btn(t(lang, "inactive_enable"), on, use_dot=True, suffix=True),
                callback_data="set:in:toggle",
            )],
            *rows_smart(
                InlineKeyboardButton(
                    text=t(lang, "inactive_reminders", count=reminders_count),
                    callback_data="set:in:reminders",
                ),
                InlineKeyboardButton(
                    text=t(lang, "inactive_hours", hours=hours),
                    callback_data="set:in:hours",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "inactive_exclude_subs"), cfg.get("inactive_exclude_subs") == "1", suffix=True),
                    callback_data="set:in:exsubs",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "inactive_return_reward"), cfg.get("inactive_return_reward") == "1", suffix=True),
                    callback_data="set:in:reward",
                ),
                InlineKeyboardButton(
                    text=t(lang, "inactive_reset", count=cfg.get("inactive_sent", "0")),
                    callback_data="set:in:reset",
                ),
            ),
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:in:help")],
            [back_button(lang, "menu:settings")],
        ]
    )


def quick_replies_kb(lang: str, replies: list) -> InlineKeyboardMarkup:
    rows = []
    for r in replies:
        preview = r.get("reply_text") or r.get("caption") or "—"
        rows.append([InlineKeyboardButton(
            text=f"/r{r['slot']} → {preview}",
            callback_data=f"set:qr:view:{r['slot']}",
        )])
    if len(replies) < 20:
        rows.append([InlineKeyboardButton(text=t(lang, "qr_add"), callback_data="set:qr:add")])
    rows.append([InlineKeyboardButton(text=t(lang, "help_section"), callback_data="set:qr:help")])
    rows.append([back_button(lang, "menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def qr_item_kb(lang: str, slot: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row(
                InlineKeyboardButton(text=t(lang, "qr_edit"), callback_data=f"set:qr:edit:{slot}"),
                InlineKeyboardButton(text=t(lang, "qr_delete"), callback_data=f"set:qr:del:{slot}"),
            ),
            [back_button(lang, "set:qreplies")],
        ]
    )


def language_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "language_ar"), callback_data="set:lang:ar")],
            [back_button(lang, "menu:settings")],
        ]
    )


# ── Finance ───────────────────────────────────────────────────────────────────

def finance_kb(lang: str, *, show_subscription_settings: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=t(lang, "fin_store"), callback_data="fin:store"),
        InlineKeyboardButton(text=t(lang, "fin_donations"), callback_data="fin:donations"),
    ]
    if show_subscription_settings:
        buttons.append(
            InlineKeyboardButton(text=t(lang, "fin_access"), callback_data="fin:access")
        )
    buttons.extend([
        InlineKeyboardButton(text=t(lang, "fin_settings"), callback_data="fin:settings"),
        InlineKeyboardButton(text=t(lang, "fin_stats"), callback_data="fin:stats"),
    ])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(*buttons),
            [back_button(lang)],
        ]
    )


# ── System & Guide ────────────────────────────────────────────────────────────

def system_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "sys_backup"), callback_data="sys:backup"),
                InlineKeyboardButton(text=t(lang, "sys_logs"), callback_data="sys:logs"),
                InlineKeyboardButton(text=t(lang, "sys_admins"), callback_data="sys:admins"),
                InlineKeyboardButton(text=t(lang, "menu_guide"), callback_data="menu:guide"),
            ),
            [back_button(lang)],
        ]
    )


def guide_sections_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "guide_settings"), callback_data="guide:settings"),
                InlineKeyboardButton(text=t(lang, "guide_content"), callback_data="guide:content"),
                InlineKeyboardButton(text=t(lang, "guide_users"), callback_data="guide:users"),
                InlineKeyboardButton(text=t(lang, "guide_subscription"), callback_data="guide:subscription"),
                InlineKeyboardButton(text=t(lang, "guide_communication"), callback_data="guide:communication"),
                InlineKeyboardButton(text=t(lang, "guide_finance"), callback_data="guide:finance"),
            ),
            [back_button(lang)],
        ]
    )
