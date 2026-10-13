# Telegram broadcast bot

An admin bot that sends one message to many chats and can repeat that post on a timer. Interface languages are Arabic and English.

## Problem

A channel owner was copying the same post into groups, private chats, and channels, then had no count of how many deliveries failed because the user had blocked the bot.

## What was built

Two entry points share the project: a personal admin bot and a public bot.

Admin panel:

- Daily statistics.
- Broadcast as a new message or as a forward.
- Audience filter: everyone, only groups and channels, or only private chats.
- Text, photo, video, document, audio, voice, and sticker.
- Live progress and a Stop button.
- A closing report: sent, blocked, failed, speed, success rate.
- A notice to the admin when someone new starts the bot.

Scheduling added on top of that:

- Repeat every 1, 3, 5, 15, or 30 minutes, or every hour.
- Target groups only, private chats only, or all.
- Turn the schedule on or off and replace the content, interval, or target without recreating the bot.

## How it works

The admin opens the broadcast menu, picks direct or forward, picks the audience, and sends the payload. The bot walks the stored chats, updates a progress message, and can be stopped mid-run. Auto-post stores the last payload plus an interval and a target, then a loop publishes it until the admin disables it. Shell helpers in the repo (`run-personal.sh`, `run-public.sh`, `deploy.sh`) are for the two processes and a VPS install. Deploy archives were left out of this public copy.

## Stack

Python, Telegram Bot API.

## Run locally

```bash
cp .env.example .env
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Create the bot in BotFather, put the token and your numeric admin id in `.env`, then start the personal or public runner.

## What this public copy leaves out

`.env`, `.env.public`, virtualenv, and the tar archives that were used to ship the bot to a server.

## Documents

- `BOTS.md` separates the owner bot (`bot/`, no Stars) from the platform (`bot_public/`), which sells a copy of the owner bot.
- `BOT_PUBLIC_TZ.md` is the platform specification: Arabic and English, a BotFather token after a Stars payment, a private database per copy, a 30-day stop, a one-day reminder, and analytics limited to the owner ids. Live account ids are not listed in that file.
