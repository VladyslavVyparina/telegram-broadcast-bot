#!/bin/bash
# Повне налаштування на VPS: venv + перевірка + запуск двох ботів
# cd /root/BOT_automatical && bash vps-setup.sh

set -e
cd "$(dirname "$0")"
PROJECT="$(pwd)"

echo "=== Проєкт: $PROJECT ==="

echo ""
echo "=== 1. Структура ==="
MISSING=0
for f in bot/main.py bot/app.py bot_public/main.py requirements.txt; do
  if [ -f "$f" ]; then
    echo "  OK  $f"
  else
    echo "  MISSING  $f"
    MISSING=1
  fi
done
if [ "$MISSING" = 1 ]; then
  echo ""
  echo "Завантажте з Mac папки bot/ і bot_public/ (без venv)."
  echo "Або: tar xzf deploy-public.tar.gz"
  exit 1
fi

if grep -q "Platform bot" bot_public/main.py 2>/dev/null; then
  echo "  OK  bot_public — нова платформа"
else
  echo "  WARN  bot_public/main.py — можливо старий код"
fi

echo ""
echo "=== 2. venv ==="
if [ ! -d venv ]; then
  echo "Створюю venv..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "  OK  venv готовий"

echo ""
echo "=== 3. Конфіги ==="
if [ ! -f .env ]; then
  echo "  MISSING .env — основний бот (ваш токен)"
  echo "  cp .env.example .env && nano .env"
else
  echo "  OK  .env"
fi
if [ ! -f .env.public ]; then
  echo "  MISSING .env.public — платформа (інший токен)"
  echo "  cp .env.public.example .env.public && nano .env.public"
else
  echo "  OK  .env.public"
fi

echo ""
echo "=== 4. Зупинка старих процесів ==="
pkill -f "python3 -m bot.main" 2>/dev/null || true
pkill -f "python3 -m bot_public.main" 2>/dev/null || true
sleep 1

echo ""
echo "=== 5. Запуск у screen ==="

if [ -f .env ]; then
  screen -dmS bot-personal bash -c "
    cd $PROJECT && source venv/bin/activate &&
    set -a && source .env && set +a &&
    exec python3 -m bot.main
  "
  echo "  OK  screen: bot-personal  (основний бот, .env)"
else
  echo "  SKIP bot-personal — немає .env"
fi

if [ -f .env.public ]; then
  screen -dmS bot-public bash -c "
    cd $PROJECT && source venv/bin/activate &&
    set -a && source .env.public && set +a &&
    exec python3 -m bot_public.main
  "
  echo "  OK  screen: bot-public   (платформа, .env.public)"
else
  echo "  SKIP bot-public — немає .env.public"
fi

echo ""
screen -ls || true
echo ""
echo "Логи:"
echo "  screen -r bot-personal"
echo "  screen -r bot-public"
echo "Вийти з логу: Ctrl+A, потім D"
