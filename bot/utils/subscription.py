"""Subscription period helpers (monthly billing)."""

DAYS_PER_MONTH = 30


def months_to_days(months: int) -> int:
    return max(1, months) * DAYS_PER_MONTH


def days_to_months(days: int) -> int:
    return max(1, round(int(days) / DAYS_PER_MONTH))


def format_months_label(months: int, lang: str = "ar") -> str:
    m = max(1, int(months))
    if lang == "ar":
        if m == 1:
            return "شهر واحد"
        if m == 2:
            return "شهرين"
        if 3 <= m <= 10:
            return f"{m} أشهر"
        return f"{m} شهر"
    if m == 1:
        return "1 month"
    return f"{m} months"
