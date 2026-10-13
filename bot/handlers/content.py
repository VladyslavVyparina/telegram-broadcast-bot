from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import (
    content_button_item_kb,
    content_buttons_kb,
    content_menu_kb,
    replies_kb,
    reply_item_kb,
    welcome_msg_kb,
)
from bot.locales import t
from bot.utils.states import ContentButtonState, ContentState

router = Router()
admin = AdminFilter()


@router.callback_query(admin, F.data == "cnt:welcome")
async def cnt_welcome(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    wm = await db.get_welcome_message()
    current = wm.get("text") or t(lang, "content_welcome_default")
    text = f"<b>{t(lang, 'content_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'content_welcome_current')}\n\n{current}"
    await callback.message.edit_text(text, reply_markup=welcome_msg_kb(lang))
    await callback.answer()


@router.callback_query(admin, F.data == "cnt:welcome:edit")
async def cnt_welcome_edit(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(ContentState.waiting_welcome)
    await callback.message.edit_text(t(lang, "content_welcome_prompt"))
    await callback.answer()


@router.callback_query(admin, F.data == "cnt:welcome:reset")
async def cnt_welcome_reset(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await db.save_welcome_message(text=None, media_type=None, file_id=None)
    replies = await db.get_auto_replies()
    btn_count = await db.count_content_buttons()
    await callback.message.edit_text(
        f"<b>{t(lang, 'content_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'content_desc')}",
        reply_markup=content_menu_kb(lang, len(replies), btn_count),
    )
    await callback.answer(t(lang, "content_welcome_saved"))


@router.message(admin, ContentState.waiting_welcome)
async def cnt_receive_welcome(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.clear()

    if message.photo:
        await db.save_welcome_message(
            text=message.caption,
            media_type="photo",
            file_id=message.photo[-1].file_id,
        )
    elif message.video:
        await db.save_welcome_message(
            text=message.caption,
            media_type="video",
            file_id=message.video.file_id,
        )
    elif message.text:
        await db.save_welcome_message(text=message.text, media_type=None, file_id=None)
    else:
        await message.answer(t(lang, "no_content"))
        return

    replies = await db.get_auto_replies()
    btn_count = await db.count_content_buttons()
    await message.answer(
        t(lang, "content_welcome_saved"),
        reply_markup=content_menu_kb(lang, len(replies), btn_count),
    )


# ── Auto replies ──────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "cnt:replies")
async def cnt_replies(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    replies = await db.get_auto_replies()
    count = len(replies)
    text = f"<b>{t(lang, 'content_replies_list', count=count)}</b>\n━━━━━━━━━━━━━━━━"
    if not replies:
        text += f"\n{t(lang, 'content_replies_empty')}"
    await callback.message.edit_text(text, reply_markup=replies_kb(lang, replies))
    await callback.answer()


@router.callback_query(admin, F.data == "cnt:rep:add")
async def cnt_reply_add(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(ContentState.waiting_trigger)
    await callback.message.edit_text(t(lang, "content_reply_trigger_prompt"))
    await callback.answer()


@router.message(admin, ContentState.waiting_trigger)
async def cnt_receive_trigger(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.update_data(trigger=message.text.strip())
    await state.set_state(ContentState.waiting_reply_text)
    await message.answer(t(lang, "content_reply_text_prompt"))


@router.message(admin, ContentState.waiting_reply_text)
async def cnt_receive_reply_text(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    data = await state.get_data()
    trigger = data.get("trigger", "")
    await state.clear()

    added = await db.add_auto_reply(trigger, message.text.strip())
    if added:
        await message.answer(t(lang, "content_reply_added"))
    else:
        await message.answer(t(lang, "content_reply_exists"))

    replies = await db.get_auto_replies()
    await message.answer(
        f"<b>{t(lang, 'content_replies_list', count=len(replies))}</b>",
        reply_markup=replies_kb(lang, replies),
    )


@router.callback_query(admin, F.data.startswith("cnt:rep:view:"))
async def cnt_reply_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    reply_id = int(callback.data.split(":")[-1])
    replies = await db.get_auto_replies()
    r = next((x for x in replies if x["id"] == reply_id), None)
    if not r:
        await callback.answer()
        return
    text = f"<b>Trigger:</b> {r['trigger']}\n<b>Reply:</b> {r['reply_text']}"
    await callback.message.edit_text(text, reply_markup=reply_item_kb(lang, reply_id))
    await callback.answer()


@router.callback_query(admin, F.data == "cnt:help")
async def cnt_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "cnt_help"), show_alert=True)


@router.callback_query(admin, F.data == "cnt:buttons")
async def cnt_buttons(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    buttons = await db.get_content_buttons()
    text = f"<b>{t(lang, 'cnt_buttons_title')}</b>\n━━━━━━━━━━━━━━━━"
    if not buttons:
        text += f"\n{t(lang, 'cnt_buttons_empty')}"
    await callback.message.edit_text(text, reply_markup=content_buttons_kb(lang, buttons))
    await callback.answer()


@router.callback_query(admin, F.data == "cnt:btn:add")
async def cnt_btn_add(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(ContentButtonState.waiting_label)
    await callback.message.edit_text(t(lang, "cnt_btn_label_prompt"))
    await callback.answer()


@router.message(admin, ContentButtonState.waiting_label)
async def cnt_btn_label(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    await state.update_data(label=message.text.strip()[:64])
    await state.set_state(ContentButtonState.waiting_url)
    await message.answer(t(lang, "cnt_btn_url_prompt"))


@router.message(admin, ContentButtonState.waiting_url)
async def cnt_btn_url(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    url = message.text.strip()
    if not url.startswith(("http://", "https://", "tg://")):
        url = f"https://{url}"
    data = await state.get_data()
    await state.clear()
    await db.add_content_button(data["label"], url)
    await message.answer(t(lang, "cnt_btn_added"))
    buttons = await db.get_content_buttons()
    await message.answer(
        t(lang, "cnt_buttons_title"),
        reply_markup=content_buttons_kb(lang, buttons),
    )


@router.callback_query(admin, F.data.startswith("cnt:btn:view:"))
async def cnt_btn_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    bid = int(callback.data.split(":")[-1])
    btn = await db.get_content_button(bid)
    if not btn:
        await callback.answer()
        return
    await callback.message.edit_text(
        f"<b>{btn['label']}</b>\n{btn['url']}",
        reply_markup=content_button_item_kb(lang, bid),
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("cnt:btn:del:"))
async def cnt_btn_del(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    bid = int(callback.data.split(":")[-1])
    await db.delete_content_button(bid)
    await callback.answer(t(lang, "cnt_btn_deleted"))
    await cnt_buttons(callback, db, config)


@router.callback_query(admin, F.data.startswith("cnt:rep:del:"))
async def cnt_reply_delete(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    reply_id = int(callback.data.split(":")[-1])
    await db.delete_auto_reply(reply_id)
    await callback.answer(t(lang, "content_reply_deleted"))
    replies = await db.get_auto_replies()
    text = f"<b>{t(lang, 'content_replies_list', count=len(replies))}</b>\n━━━━━━━━━━━━━━━━"
    if not replies:
        text += f"\n{t(lang, 'content_replies_empty')}"
    await callback.message.edit_text(text, reply_markup=replies_kb(lang, replies))
