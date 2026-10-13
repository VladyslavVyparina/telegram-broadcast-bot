# Two bots

## `bot/` — the owner’s bot

- The full autopost feature set
- No Telegram Stars charge
- Start with `python3 -m bot.main`

## `bot_public/` — the platform that creates bots

- A user pays in Stars and gets their own copy of `bot/`
- Languages: Arabic and English
- The specification is [BOT_PUBLIC_TZ.md](BOT_PUBLIC_TZ.md)
- From the project root, with the public env file loaded:

```bash
set -a && source .env.public && set +a
python3 -m bot_public.main
```

Platform admin ids belong in `.env.public`, not in this page. The working copy named three numeric Telegram ids; set those only on the server.

## Telegram Stars

Stars stay on the bot’s balance inside Telegram. This code cannot transfer Stars to a personal account. Only Telegram does that, and only the BotFather owner of that bot sees the balance.

BotFather, `/mybots`, the platform bot, Balance.

`STARS_OWNER_ID` in `.env.public` is who receives the payment notice. For that person to receive the Stars themselves, that account has to be the bot owner in BotFather.
