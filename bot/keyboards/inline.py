from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.layout import row, rows_smart
from bot.locales import t


def back_button(lang: str, callback: str = "menu:main") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, "back"), callback_data=callback)


from bot.keyboards.menus import main_menu_kb  # noqa: F401 — re-export


def build_content_buttons_kb(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    rows_map: dict[int, list] = {}
    for b in buttons:
        row_pos = int(b.get("row_pos", 0))
        rows_map.setdefault(row_pos, []).append(
            InlineKeyboardButton(text=b["label"], url=b["url"])
        )
    rows = [rows_map[k] for k in sorted(rows_map.keys())]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_sub_check_kb(lang: str, subs: list, show_verify: bool = True) -> InlineKeyboardMarkup:
    rows = []
    for s in subs:
        if s.get("invite_link"):
            title = s.get("title") or s.get("username") or "Channel"
            rows.append([InlineKeyboardButton(text=f"📢 {title}", url=s["invite_link"])])
        elif s.get("username"):
            uname = s["username"].lstrip("@")
            rows.append([InlineKeyboardButton(text=f"📢 @{uname}", url=f"https://t.me/{uname}")])
    if show_verify:
        rows.append([InlineKeyboardButton(text=t(lang, "sub_check_btn"), callback_data="sub:check")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_buttons_kb(lang: str, buttons: list) -> InlineKeyboardMarkup:
    rows = []
    for b in buttons:
        rows.append([
            InlineKeyboardButton(
                text=f"🔘 {b['label']}",
                callback_data=f"cnt:btn:view:{b['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t(lang, "cnt_btn_add"), callback_data="cnt:btn:add")])
    rows.append([back_button(lang, "menu:content")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_button_item_kb(lang: str, button_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row(
                InlineKeyboardButton(text=t(lang, "cnt_btn_delete"), callback_data=f"cnt:btn:del:{button_id}"),
                back_button(lang, "cnt:buttons"),
            ),
        ]
    )


# ── Communication ─────────────────────────────────────────────────────────────

def communication_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "quick_broadcast"), callback_data="com:quick"),
                InlineKeyboardButton(text=t(lang, "broadcast_menu"), callback_data="com:broadcast"),
                InlineKeyboardButton(text=t(lang, "forward_messages"), callback_data="com:forward"),
            ),
            [back_button(lang)],
        ]
    )


# ── Broadcast ─────────────────────────────────────────────────────────────────

def broadcast_method_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "direct_message"), callback_data="bc:method:direct"),
                InlineKeyboardButton(text=t(lang, "forward_message"), callback_data="bc:method:forward"),
            ),
            [back_button(lang, "menu:communication")],
        ]
    )


def broadcast_audience_kb(lang: str, method: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "audience_all"), callback_data=f"bc:audience:all:{method}"),
                InlineKeyboardButton(text=t(lang, "audience_groups"), callback_data=f"bc:audience:groups:{method}"),
                InlineKeyboardButton(text=t(lang, "audience_private"), callback_data=f"bc:audience:private:{method}"),
            ),
            [back_button(lang, "com:broadcast")],
        ]
    )


def content_prompt_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "supported_formats"), callback_data="bc:formats")],
            [back_button(lang, "menu:communication")],
        ]
    )


def stop_broadcast_kb(lang: str, broadcast_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "stop"), callback_data=f"bc:stop:{broadcast_id}")],
        ]
    )


def broadcast_done_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[back_button(lang, "menu:communication")]],
    )


# ── Content ───────────────────────────────────────────────────────────────────

def content_menu_kb(lang: str, replies_count: int = 0, buttons_count: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(
                    text=t(lang, "cnt_auto_replies", count=replies_count),
                    callback_data="cnt:replies",
                ),
                InlineKeyboardButton(text=t(lang, "welcome_msg_btn"), callback_data="cnt:welcome"),
                InlineKeyboardButton(
                    text=t(lang, "cnt_buttons_count", count=buttons_count),
                    callback_data="cnt:buttons",
                ),
                InlineKeyboardButton(text=t(lang, "cnt_subscription"), callback_data="menu:subscription"),
            ),
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="cnt:help")],
            [back_button(lang)],
        ]
    )


def welcome_msg_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "cnt_edit_welcome"), callback_data="cnt:welcome:edit"),
                InlineKeyboardButton(text=t(lang, "content_welcome_reset"), callback_data="cnt:welcome:reset"),
            ),
            [back_button(lang, "menu:content")],
        ]
    )


def replies_kb(lang: str, replies: list) -> InlineKeyboardMarkup:
    rows = []
    for r in replies:
        rows.append([
            InlineKeyboardButton(
                text=f"/{r['trigger']} → {r['reply_text']}",
                callback_data=f"cnt:rep:view:{r['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t(lang, "content_replies_add"), callback_data="cnt:rep:add")])
    rows.append([back_button(lang, "menu:content")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reply_item_kb(lang: str, reply_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row(
                InlineKeyboardButton(text=t(lang, "content_replies_delete"), callback_data=f"cnt:rep:del:{reply_id}"),
                back_button(lang, "cnt:replies"),
            ),
        ]
    )


# ── Subscription ──────────────────────────────────────────────────────────────

from bot.utils.toggle import toggle_btn


def subscription_kb(lang: str, enabled: bool, count: int, notify: bool, grouped: bool = True, verify_btn: bool = False) -> InlineKeyboardMarkup:
    notify_label = toggle_btn(t(lang, "sub_notification_label"), notify, suffix=True)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "sub_add_count", count=count),
                callback_data="sub:add",
            )],
            [sep_button(lang, "sub_settings_sep")],
            [InlineKeyboardButton(text=notify_label, callback_data="sub:notify:toggle")],
            [sep_button(lang, "sub_display_sep")],
            *rows_smart(
                InlineKeyboardButton(
                    text=t(lang, "sub_display_grouped" if grouped else "sub_display_single"),
                    callback_data="sub:display:toggle",
                ),
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "sub_verify_button"), verify_btn, suffix=True),
                    callback_data="sub:verify:toggle",
                ),
            ),
            [InlineKeyboardButton(
                text=t(lang, "sub_grouped_message"),
                callback_data="sub:grouped:msg",
            )],
            [InlineKeyboardButton(
                text=toggle_btn(t(lang, "sub_enable_label"), enabled, use_dot=True, suffix=True),
                callback_data="sub:toggle",
            )],
            [InlineKeyboardButton(text=t(lang, "help_section"), callback_data="sub:help")],
            [back_button(lang)],
        ]
    )


def sep_button(lang: str, key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, key), callback_data="noop")


def sub_list_kb(lang: str, subs: list) -> InlineKeyboardMarkup:
    rows = []
    for s in subs:
        title = s.get("title") or s.get("username") or str(s["chat_id"])
        rows.append([
            InlineKeyboardButton(text=f"🏠 {title}", callback_data=f"sub:view:{s['id']}"),
        ])
    rows.append([back_button(lang, "menu:subscription")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sub_item_kb(lang: str, sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row(
                InlineKeyboardButton(text=t(lang, "sub_remove"), callback_data=f"sub:del:{sub_id}"),
                back_button(lang, "sub:list"),
            ),
        ]
    )


# ── Users ─────────────────────────────────────────────────────────────────────

def users_menu_kb(lang: str, banned_count: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "users_search"), callback_data="usr:search"),
                InlineKeyboardButton(
                    text=t(lang, "users_banned_list").format(count=banned_count),
                    callback_data="usr:banned",
                ),
            ),
            [back_button(lang)],
        ]
    )


def user_card_kb(lang: str, user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    if is_banned:
        action_btn = InlineKeyboardButton(
            text=t(lang, "unban_user_btn"), callback_data=f"usr:unban:{user_id}"
        )
    else:
        action_btn = InlineKeyboardButton(
            text=t(lang, "ban_user_btn"), callback_data=f"usr:ban:{user_id}"
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [action_btn],
            [back_button(lang, "menu:users")],
        ]
    )


def banned_list_kb(lang: str, banned: list) -> InlineKeyboardMarkup:
    rows = []
    for u in banned[:20]:
        name = u.get("first_name") or u.get("username") or str(u["user_id"])
        rows.append([
            InlineKeyboardButton(
                text=f"🚫 {name} ({u['user_id']})",
                callback_data=f"usr:card:{u['user_id']}",
            )
        ])
    rows.append([back_button(lang, "menu:users")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Settings (legacy re-export) ───────────────────────────────────────────────

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    from bot.keyboards.menus import language_kb
    return language_kb(lang)


# ── Auto post ─────────────────────────────────────────────────────────────────

from bot.database.db import MAX_AUTOPOST_ITEMS
from bot.utils.helpers import content_preview


def autopost_menu_kb(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if enabled:
        rows.append([InlineKeyboardButton(text=t(lang, "disable"), callback_data="ap:disable")])
        rows.append([InlineKeyboardButton(text=t(lang, "ap_manage_messages"), callback_data="ap:items")])
        rows.extend(rows_smart(
            InlineKeyboardButton(text=t(lang, "change_interval"), callback_data="ap:interval"),
            InlineKeyboardButton(text=t(lang, "change_target"), callback_data="ap:target"),
        ))
    else:
        rows.append([InlineKeyboardButton(text=t(lang, "enable"), callback_data="ap:setup")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def autopost_items_kb(
    lang: str, items: list, *, enabled: bool, setup_mode: bool = False
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, item in enumerate(items, start=1):
        preview = content_preview(item["content"])
        rows.append([
            InlineKeyboardButton(
                text=f"#{idx} {preview}",
                callback_data=f"ap:item:view:{item['id']}",
            )
        ])
    if len(items) < MAX_AUTOPOST_ITEMS:
        rows.append([
            InlineKeyboardButton(text=t(lang, "ap_add_item"), callback_data="ap:item:add")
        ])
    if items and (setup_mode or not enabled):
        rows.append([
            InlineKeyboardButton(text=t(lang, "ap_start"), callback_data="ap:start")
        ])
    back_cb = "menu:autopost" if enabled or not setup_mode else "menu:autopost"
    rows.append([back_button(lang, back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def autopost_item_kb(lang: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "ap_edit_item"), callback_data=f"ap:item:edit:{item_id}")],
            [InlineKeyboardButton(text=t(lang, "ap_delete_item"), callback_data=f"ap:item:del:{item_id}")],
            [back_button(lang, "ap:items")],
        ]
    )


def autopost_interval_kb(lang: str) -> InlineKeyboardMarkup:
    intervals = [
        (300, "interval_5m"),
        (900, "interval_15m"),
        (1800, "interval_30m"),
        (3600, "interval_60m"),
    ]
    rows = []
    for i in range(0, len(intervals), 2):
        pair = []
        for seconds, label in intervals[i : i + 2]:
            pair.append(InlineKeyboardButton(text=t(lang, label), callback_data=f"ap:int:{seconds}"))
        rows.append(pair)
    rows.append([back_button(lang, "menu:autopost")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def autopost_target_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *rows_smart(
                InlineKeyboardButton(text=t(lang, "autopost_target_groups"), callback_data="ap:tgt:groups"),
                InlineKeyboardButton(text=t(lang, "autopost_target_private"), callback_data="ap:tgt:private"),
                InlineKeyboardButton(text=t(lang, "autopost_target_all"), callback_data="ap:tgt:all"),
            ),
            [back_button(lang, "menu:autopost")],
        ]
    )
