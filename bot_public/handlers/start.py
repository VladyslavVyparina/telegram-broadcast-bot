from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_public.config import Config, is_platform_owner
from bot_public.database.db import PlatformDB
from bot_public.keyboards.common import language_kb, main_kb
from bot_public.locales import t

router = Router()


async def _lang(platform_db: PlatformDB, user_id: int) -> str:
    return await platform_db.get_user_language(user_id)


async def _main_menu(
    platform_db: PlatformDB, user_id: int, name: str, lang: str,
) -> tuple[str, object]:
    paid = await platform_db.is_paid_mode()
    text = t(lang, "welcome", name=name)
    kb = main_kb(lang, show_admin=is_platform_owner(user_id), paid_mode=paid)
    return text, kb


@router.message(CommandStart())
async def cmd_start(
    message: Message, platform_db: PlatformDB, config: Config, state: FSMContext,
) -> None:
    user = message.from_user
    if not user:
        return
    await state.clear()
    existing = await platform_db.get_user(user.id)
    await platform_db.upsert_user(user.id, user.username, user.first_name)

    if not existing or existing.get("language") not in ("ar", "en"):
        await message.answer(
            t(config.default_language, "choose_language"),
            reply_markup=language_kb(),
        )
        return

    lang = await _lang(platform_db, user.id)
    name = user.first_name or user.username or "—"
    text, kb = await _main_menu(platform_db, user.id, name, lang)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.in_(("lang:ar", "lang:en")))
async def set_language(callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext) -> None:
    if not callback.from_user:
        return
    code = callback.data.split(":")[-1]
    await platform_db.upsert_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
    )
    await platform_db.set_user_language(callback.from_user.id, code)
    lang = code
    name = callback.from_user.first_name or callback.from_user.username or "—"
    text = t(lang, "language_saved") + "\n\n" + t(lang, "welcome", name=name)
    _, kb = await _main_menu(platform_db, callback.from_user.id, name, lang)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "lang:menu")
async def language_menu(callback: CallbackQuery, platform_db: PlatformDB) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.message.edit_text(
        t(lang, "choose_language"),
        reply_markup=language_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def menu_main(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user:
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    name = callback.from_user.first_name or callback.from_user.username or "—"
    text, kb = await _main_menu(platform_db, callback.from_user.id, name, lang)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
