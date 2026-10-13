#!/bin/bash
# Виправлення @Ni_iF7Fibot на VPS
# cd /root/BOT_automatical && bash fix-public-vps.sh

set -e
cd "$(dirname "$0")"

echo "=== 1. Перевірка create.py ==="
if ! grep -q 'F.data == "pay:method:crypto"' bot_public/handlers/create.py; then
  echo "ERROR: bot_public/handlers/create.py — немає обробника pay:method:crypto"
  echo "Завантажте файл з Mac:"
  echo "  scp bot_public/handlers/create.py root@VPS:/root/BOT_automatical/bot_public/handlers/create.py"
  exit 1
fi
if grep -q 'waiting_crypto_proof' bot_public/handlers/create.py; then
  echo "ERROR: create.py застарілий (waiting_crypto_proof)"
  exit 1
fi
echo "OK create.py"

echo ""
echo "=== 2. Перевірка common.py ==="
if grep -q 'pay:crypto:sent' bot_public/keyboards/common.py; then
  echo "ERROR: common.py застарілий (кнопка pay:crypto:sent)"
  exit 1
fi
echo "OK common.py"

echo ""
echo "=== 3. Імпорт ==="
source venv/bin/activate
set -a && source .env.public && set +a
python3 -c "from bot_public.main import main; print('IMPORT OK')"

echo ""
echo "=== 4. Перезапуск ==="
pkill -f "python3 -m bot_public.main" 2>/dev/null || true
screen -S bot-public -X quit 2>/dev/null || true
sleep 2
screen -dmS bot-public bash -c "cd $(pwd) && source venv/bin/activate && set -a && source .env.public && set +a && python3 -m bot_public.main"
sleep 3
pgrep -af "bot_public.main" || { echo "ERROR: бот не запустився"; exit 1; }
echo "DONE — напишіть /start боту @Ni_iF7Fibot"
