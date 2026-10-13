# Telegram-розсилка

Бот для розсилки і відкладеного постингу в групи, канали і приватні чати. Є адмін-панель зі статистикою і окремий публічний бот.

**Стек.** Python, Telegram.

Публічний кейс. Робоча копія з паролями і базами лишається локально і сюди не входить.

---

# Telegram Broadcast Bot (بوتي)

Telegram bot for mass broadcasting and automatic posting to groups, private chats, and channels.

Based on reference bot [@sftsfdrtghbot](https://t.me/sftsfdrtghbot) with added auto-post scheduling.

## Features

### From reference bot
- Admin control panel with daily statistics
- Broadcast menu (Direct message / Forward message)
- Audience targeting: All / Groups & Channels / Private only
- Media support: text, photos, videos, documents, audio, voice, stickers
- Live broadcast progress with Stop button
- Completion report (sent, blocked, failed, speed, success %)
- New user notifications to admin
- Arabic + English interface with language switch

### Additional (client requirements)
- Auto-post at intervals: 1, 3, 5, 15, 30 minutes, 1 hour
- Auto-post targets: Groups only / Private only / All
- Enable/disable auto-post, change content/interval/target anytime

## Setup

### 1. Create bot
1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token

### 2. Get your Telegram ID
1. Open [@userinfobot](https://t.me/userinfobot)
2. Copy your numeric user ID

### 3. Configure
```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_token_here
ADMIN_ID=your_telegram_id
DEFAULT_LANGUAGE=ar
DATABASE_PATH=bot.db
```

### 4. Install & run
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

## Usage

1. Start the bot: `/start` (as admin you see the control panel)
2. Add the bot to groups/channels (give it permission to send messages)
3. **Manual broadcast:** Broadcast → method → audience → send content
4. **Auto-post:** Auto Post → Enable → interval → target → send content

## Project structure

```
bot/
  main.py              # Entry point
  config.py            # Environment config
  database/db.py       # SQLite storage
  handlers/            # Command & callback handlers
  keyboards/inline.py  # Inline keyboards
  locales/             # Arabic & English texts
  services/            # Broadcast engine & scheduler
  filters/admin.py     # Admin access filter
```

## Deploy (VPS)

Run with systemd or screen/tmux so the bot stays online 24/7:

```bash
screen -S broadcast-bot
source venv/bin/activate
python -m bot.main
# Ctrl+A, D to detach
```

## Notes

- Telegram may rate-limit or restrict bots used for mass messaging
- Bot can only post where it has been added with send permissions
- Keep your `.env` file secret — never commit it to git
