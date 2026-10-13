from bot_public.locales.ar import TEXTS as AR
from bot_public.locales.en import TEXTS as EN

LOCALES = {"ar": AR, "en": EN}


def t(lang: str, key: str, **kwargs) -> str:
    texts = LOCALES.get(lang, AR)
    template = texts.get(key, AR.get(key, key))
    if kwargs:
        return template.format(**kwargs)
    return template
