#!/bin/bash
# Деплой платформи bot_public + залежність bot/
# На Mac: ./deploy-public.sh VPS_IP

set -e
IP="${1:?Usage: ./deploy-public.sh VPS_IP}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Packing bot + bot_public..."
tar czf "$DIR/deploy-public.tar.gz" -C "$DIR" bot bot_public run-public.sh

echo "==> Uploading..."
scp "$DIR/deploy-public.tar.gz" "root@$IP:/root/BOT_automatical/"

echo "==> Extracting on VPS..."
ssh "root@$IP" 'cd /root/BOT_automatical && tar xzf deploy-public.tar.gz && rm deploy-public.tar.gz && echo OK'

echo ""
echo "На VPS виконайте:"
echo "  cd /root/BOT_automatical"
echo "  source venv/bin/activate"
echo "  test -f .env.public || cp .env.public.example .env.public"
echo "  set -a && source .env.public && set +a"
echo "  python3 -m bot_public.main   # перевірка (Ctrl+C після OK)"
echo "  screen -dmS bot-public bash -c 'cd /root/BOT_automatical && source venv/bin/activate && set -a && source .env.public && set +a && python3 -m bot_public.main'"
