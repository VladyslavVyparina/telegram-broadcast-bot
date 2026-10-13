from __future__ import annotations

from aiogram.types import InlineKeyboardButton


def row(*buttons: InlineKeyboardButton) -> list[InlineKeyboardButton]:
    return list(buttons)


def row_wide(button: InlineKeyboardButton) -> list[list[InlineKeyboardButton]]:
    return [[button]]


def _text_len(btn: InlineKeyboardButton) -> int:
    return len(btn.text or "")


def rows_smart(
    *buttons: InlineKeyboardButton,
    max_len: int = 15,
    wide_at: int = 16,
) -> list[list[InlineKeyboardButton]]:
    """
    Like the reference bot: pair short labels in two columns,
    place long labels on their own full-width row.
    Short buttons before a long one are paired first; leftovers stay wide.
    """
    rows: list[list[InlineKeyboardButton]] = []
    pending: list[InlineKeyboardButton] = []

    def is_wide(btn: InlineKeyboardButton) -> bool:
        n = _text_len(btn)
        return n >= wide_at or n > max_len

    def flush() -> None:
        nonlocal pending
        i = 0
        while i < len(pending):
            if (
                i + 1 < len(pending)
                and not is_wide(pending[i])
                and not is_wide(pending[i + 1])
            ):
                rows.append([pending[i], pending[i + 1]])
                i += 2
            else:
                rows.append([pending[i]])
                i += 1
        pending = []

    for btn in buttons:
        if is_wide(btn):
            flush()
            rows.append([btn])
        else:
            pending.append(btn)
    flush()
    return rows


def rows_two(*buttons: InlineKeyboardButton) -> list[list[InlineKeyboardButton]]:
    """Always two per row (legacy helper)."""
    btns = list(buttons)
    return [btns[i : i + 2] for i in range(0, len(btns), 2)]
