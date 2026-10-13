#!/bin/bash
# Deploy bot to VPS — run from Mac:
#   chmod +x deploy.sh
#   ./deploy.sh YOUR_VPS_IP

set -e
IP="${1:?Usage: ./deploy.sh VPS_IP}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Packing bot..."
tar czf "$DIR/deploy-bot.tar.gz" -C "$DIR" bot

echo "==> Uploading to root@$IP..."
scp "$DIR/deploy-bot.tar.gz" "root@$IP:/root/BOT_automatical/"

echo "==> Extracting on server..."
ssh "root@$IP" 'cd /root/BOT_automatical && tar xzf deploy-bot.tar.gz && rm deploy-bot.tar.gz && echo OK'

echo ""
echo "Done! Now on VPS run:"
echo "  screen -d -r telegram-bot   # or: screen -S telegram-bot"
echo "  cd /root/BOT_automatical && source venv/bin/activate"
echo "  python3 -m bot.main"
