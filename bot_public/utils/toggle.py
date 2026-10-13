"""Toggle button helpers — green ✅/🟢 when ON, red ❌/🔴 when OFF."""


def icon(on: bool) -> str:
    return "✅" if on else "❌"


def dot(on: bool) -> str:
    return "🟢" if on else "🔴"


def toggle_btn(label: str, on: bool, *, use_dot: bool = False, suffix: bool = False) -> str:
    mark = dot(on) if use_dot else icon(on)
    if suffix:
        return f"{label} {mark}"
    return f"{mark} {label}"
