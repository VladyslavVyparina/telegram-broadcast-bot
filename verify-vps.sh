#!/bin/bash
# Перевірка VPS перед запуском: токени, Crypto Pay, БД, процеси
# cd /root/BOT_automatical && bash verify-vps.sh

set -e
cd "$(dirname "$0")"
PROJECT="$(pwd)"

echo "========== 1. venv =========="
if [ -x "$PROJECT/venv/bin/python3" ]; then
  echo "  OK  $PROJECT/venv/bin/python3"
  # shellcheck disable=SC1091
  source "$PROJECT/venv/bin/activate"
else
  echo "  FAIL  немає venv — python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi

echo ""
echo "========== 2. .env.public — BOT_TOKEN (@Ni_iF7Fibot) =========="
if [ ! -f .env.public ]; then
  echo "  FAIL  немає .env.public"
  exit 1
fi
set -a && source .env.public && set +a
if [ -z "${BOT_TOKEN:-}" ]; then
  echo "  FAIL  BOT_TOKEN порожній у .env.public"
  exit 1
fi
RESP=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('ok'):
    r = d['result']
    print(f\"  OK  @{r.get('username')} ({r.get('first_name')})\")
else:
    print(f\"  FAIL  {d.get('description', d)}\")
    print('  → Відкрий BotFather, скопіюй токен @Ni_iF7Fibot у .env.public')
    sys.exit(1)
" || exit 1

echo ""
echo "========== 3. .env — основний бот =========="
if [ -f .env ]; then
  set -a && source .env && set +a
  RESP=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
  echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('ok'):
    r = d['result']
    print(f\"  OK  @{r.get('username')}\")
else:
    print(f\"  FAIL  {d.get('description', d)}\")
"
else
  echo "  SKIP  немає .env"
fi

echo ""
echo "========== 4. Crypto Pay (@CryptoBot) =========="
set -a && source .env.public && set +a
if [ -z "${CRYPTO_PAY_API_TOKEN:-}" ]; then
  echo "  WARN  CRYPTO_PAY_API_TOKEN не заданий — крипто-оплата вимкнена"
else
  HOST="pay.crypt.bot"
  [ "${CRYPTO_PAY_TESTNET:-0}" = "1" ] && HOST="testnet-pay.crypt.bot"
  RESP=$(curl -s -H "Crypto-Pay-API-Token: ${CRYPTO_PAY_API_TOKEN}" \
    "https://${HOST}/api/getMe")
  echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('ok'):
    r = d.get('result', d.get('data', {}))
    name = r.get('name') or r.get('app_id') or 'app'
    print(f'  OK  Crypto Pay app: {name}')
else:
    print(f\"  FAIL  {d}\")
    print('  → Перевір CRYPTO_PAY_API_TOKEN у @CryptoBot → Crypto Pay')
"
fi

echo ""
echo "========== 5. Імпорт Python =========="
python3 -c "from bot_public.main import main; from bot.main import main as m2; print('  OK  bot_public + bot')"

echo ""
echo "========== 6. Клони в БД =========="
DB="${DATABASE_PATH:-bot_public.db}"
python3 <<PY
import sqlite3, json
from datetime import datetime, timezone
db = "${DB}"
try:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, bot_username, expires_at, is_running, "
        "substr(bot_token,1,12) AS tok FROM child_bots ORDER BY id"
    ).fetchall()
    if not rows:
        print("  (немає клонів у child_bots)")
    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        exp = r["expires_at"] or ""
        active = "ACTIVE" if exp > now.replace("+00:00", "Z")[:19] else "EXPIRED"
        print(f"  id={r['id']} @{r['bot_username'] or '?'} {active} running={r['is_running']} token={r['tok']}...")
    conn.close()
except Exception as e:
    print(f"  FAIL  {e}")
PY

echo ""
echo "========== 7. Процеси =========="
pgrep -af "python3 -m bot" || echo "  (немає процесів)"
echo ""
CLONES=$(pgrep -cf "python3 -m bot.clone_main" 2>/dev/null || echo 0)
PUBLIC=$(pgrep -cf "python3 -m bot_public.main" 2>/dev/null || echo 0)
echo "  bot_public: $PUBLIC | клони: $CLONES"

echo ""
echo "========== Готово =========="
if [ "$PUBLIC" -eq 0 ]; then
  echo "Запуск: bash restart-all.sh"
  echo "Лог:    screen -r bot-public"
fi
