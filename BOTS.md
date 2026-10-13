# Два боти

## `bot/` — основний (ваш особистий)
- Повний функціонал автопостингу
- Без оплати Stars
- `python3 -m bot.main`

## `bot_public/` — платформа (творець ботів)
- Користувачі платять Stars і створюють **власну копію** `bot/`
- Мови: **арабська + англійська**
- ТЗ: [BOT_PUBLIC_TZ.md](BOT_PUBLIC_TZ.md)
- Запуск з кореня проєкту:

```bash
cd /root/BOT_automatical
source venv/bin/activate
set -a && source .env.public && set +a
screen -dmS bot-public python3 -m bot_public.main
```

Адміни платформи (ціна/аналітика): `865883330`, `8734758541`, `929743223`

## Telegram Stars (оплата)

Зірки **не зникають** — вони на балансі бота **@Ni_iF7Fibot** у Telegram.

- Код **не може** перевести Stars на особистий акаунт за ID — це робить лише Telegram.
- Баланс бачить **власник бота в BotFather** (акаунт, який створив `@Ni_iF7Fibot`).
- Щоб Stars отримував ID `929743223` — цей акаунт має бути власником бота в BotFather.
- Перегляд: BotFather → `/mybots` → `Ni_iF7Fibot` → **Balance**
- У `.env.public`: `STARS_OWNER_ID=929743223` (сповіщення про оплати)
