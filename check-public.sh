#!/bin/bash
# Діагностика bot_public на VPS
# cd /root/BOT_automatical && bash check-public.sh

set -e
cd "$(dirname "$0")"

echo "=== 1. Структура ==="
test -f bot/app.py && echo "OK bot/app.py" || echo "MISSING bot/app.py — завантажте папку bot/!"
test -f bot_public/main.py && echo "OK bot_public/main.py" || echo "MISSING bot_public/"
test -f .env.public && echo "OK .env.public" || echo "MISSING .env.public"

echo ""
echo "=== 2. Процеси ==="
pgrep -af "bot_public" || echo "(немає процесу bot_public)"
pgrep -af "bot.main" || true

echo ""
echo "=== 3. Screen ==="
screen -ls || true

echo ""
echo "=== 4. Тест імпорту ==="
if [ -d venv ]; then source venv/bin/activate; fi
if [ -f .env.public ]; then set -a && source .env.public && set +a; fi
python3 -c "
from bot.app import run_bot_instance
from bot_public.main import main
from bot_public.handlers.start import router
print('IMPORT OK')
" 2>&1 || echo "IMPORT FAILED — дивіться помилку вище"

echo ""
echo "=== 5. Запуск на 5 сек (перевірка старту) ==="
timeout 5 python3 -m bot_public.main 2>&1 || true
