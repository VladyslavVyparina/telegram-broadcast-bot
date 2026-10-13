#!/bin/bash
# Повний перезапуск: @Ni_iF7Fibot + клони + особистий бот
# cd /root/BOT_automatical && bash restart-all.sh

set -e
cd "$(dirname "$0")"
PROJECT="$(pwd)"
mkdir -p data/clones data/clones/logs

if [ ! -x "$PROJECT/venv/bin/python3" ]; then
  echo "ERROR: немає venv — спочатку:"
  echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "==> Зупинка всіх процесів..."
pkill -9 -f "python3 -m bot.clone_main" 2>/dev/null || true
pkill -9 -f "python3 -m bot_public.main" 2>/dev/null || true
pkill -9 -f "python3 -m bot.main" 2>/dev/null || true
sleep 2
screen -S bot-public -X quit 2>/dev/null || true
screen -S bot-personal -X quit 2>/dev/null || true
screen -wipe 2>/dev/null || true

# shellcheck disable=SC1091
source "$PROJECT/venv/bin/activate"

echo "==> Перевірка імпорту..."
if [ ! -f .env.public ]; then
  echo "ERROR: немає .env.public"
  exit 1
fi
set -a && source .env.public && set +a
python3 -c "from bot_public.main import main; from bot.clone_main import main as cm; print('IMPORT OK')"

echo "==> Запуск bot-public (клони стартують автоматично)..."
screen -dmS bot-public bash -c "
  cd '$PROJECT' &&
  source venv/bin/activate &&
  set -a && source .env.public && set +a &&
  exec python3 -m bot_public.main
"

if [ -f .env ]; then
  echo "==> Запуск bot-personal..."
  screen -dmS bot-personal bash -c "
    cd '$PROJECT' &&
    source venv/bin/activate &&
    set -a && source .env && set +a &&
    exec python3 -m bot.main
  "
fi

sleep 6
echo ""
echo "==> Процеси:"
pgrep -af "python3 -m bot" || echo "(немає процесів!)"

echo ""
echo "==> Screen:"
screen -ls || true

CLONES=$(pgrep -cf "python3 -m bot.clone_main" 2>/dev/null || echo 0)
PUBLIC=$(pgrep -cf "python3 -m bot_public.main" 2>/dev/null || echo 0)
echo ""
echo "==> bot_public: $PUBLIC | клонів: $CLONES"

if [ "$PUBLIC" -eq 0 ]; then
  echo ""
  echo "⚠️  bot_public НЕ ЗАПУЩЕНИЙ! Дивіться помилку:"
  echo "  screen -r bot-public"
  echo "  або: cd $PROJECT && source venv/bin/activate && set -a && source .env.public && set +a && python3 -m bot_public.main"
fi

if [ "$CLONES" -eq 0 ]; then
  echo "⚠️  клони не запущені — bash check-clones.sh"
  echo "  логи клонів: tail -20 data/clones/logs/clone_*.log"
fi

echo ""
echo "Діагностика: bash check-clones.sh"
