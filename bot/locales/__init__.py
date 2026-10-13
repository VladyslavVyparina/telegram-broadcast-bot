from bot.locales.ar import TEXTS as AR
from bot.locales.en import TEXTS as EN
from bot.locales.extended_ar import EXTENDED as AR_EXT
from bot.locales.extended_en import EXTENDED as EN_EXT

AR = {**AR, **AR_EXT}
EN = {**EN, **EN_EXT}

LOCALES = {"ar": AR, "en": EN}


def t(lang: str, key: str, **kwargs) -> str:
    texts = LOCALES.get(lang, AR)
    template = texts.get(key, AR.get(key, key))
    if kwargs:
        return template.format(**kwargs)
    return template
