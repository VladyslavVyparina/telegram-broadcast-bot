#!/bin/bash
# Діагностика клонів bot_public на VPS
set -e
cd "$(dirname "$0")"
if [ -f .env.public ]; then
  set -a && source .env.public && set +a
fi
DB="${DATABASE_PATH:-bot_public.db}"

echo "========== 1. Процеси Python =========="
pgrep -af "python3 -m bot" || echo "(немає процесів)"

echo ""
echo "========== 2. Screen-сесії =========="
screen -ls 2>/dev/null || true

echo ""
echo "========== 3. Клони в БД ($DB) =========="
python3 <<PY
import sqlite3
from datetime import datetime, timezone
db = "${DB}"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, owner_id, bot_username, expires_at, is_running, "
    "substr(bot_token,1,15) AS token FROM child_bots ORDER BY id"
).fetchall()
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
print(f"UTC now: {now}")
if not rows:
    print("(немає child_bots)")
for r in rows:
    exp = r["expires_at"] or ""
    st = "ACTIVE" if exp[:19] > now else "EXPIRED"
    print(f"id={r['id']} owner={r['owner_id']} @{r['bot_username'] or '?'} "
          f"{st} running={r['is_running']} token={r['token']}...")
conn.close()
PY

echo ""
echo "========== 4. Прострочені? =========="
python3 <<PY
import sqlite3
db = "${DB}"
conn = sqlite3.connect(db)
for r in conn.execute(
    "SELECT id, bot_username, expires_at FROM child_bots"
).fetchall():
    print(r)
conn.close()
PY

echo ""
echo "========== 5. Токени через Telegram API =========="
python3 <<PY
import sqlite3, json, urllib.request
db = "${DB}"
conn = sqlite3.connect(db)
for (token,) in conn.execute("SELECT bot_token FROM child_bots"):
    if not token or token.startswith("virtual:"):
        continue
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getMe", timeout=10
        ) as resp:
            d = json.load(resp)
        u = d.get("result", {}).get("username", "?") if d.get("ok") else d.get("description")
        print(f"  {token[:20]}... -> {d.get('ok')} @{u}")
    except Exception as e:
        print(f"  {token[:20]}... -> ERROR {e}")
conn.close()
PY

echo ""
echo "========== 6. Логи клонів (останні рядки) =========="
if ls data/clones/logs/clone_*.log 1>/dev/null 2>&1; then
  for f in data/clones/logs/clone_*.log; do
    echo "--- $f ---"
    tail -5 "$f" 2>/dev/null || true
  done
else
  echo "  (немає data/clones/logs/clone_*.log)"
fi

echo ""
echo "========== 7. Швидкий тест імпорту клону =========="
python3 <<'PY'
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from bot.config import Config
from bot.database.db import Database

async def test():
  db_path = list(Path("data/clones").glob("*.db"))
  if not db_path:
    print("  (немає файлів data/clones/*.db)")
    return
  p = str(db_path[0])
  cfg = Config.from_values(bot_token="x:y", admin_id=1, database_path=p)
  d = Database(cfg.database_path)
  await d.connect()
  await d.close()
  print(f"  OK: clone DB readable ({p})")

asyncio.run(test())
PY

echo ""
echo "========== 8. Останні рядки логу bot-public =========="
if screen -list 2>/dev/null | grep -q bot-public; then
  screen -S bot-public -X hardcopy /tmp/bot-public-check.log 2>/dev/null || true
  tail -30 /tmp/bot-public-check.log 2>/dev/null || echo "(не вдалось прочитати screen)"
else
  echo "⚠️  screen bot-public НЕ ЗНАЙДЕНО — платформа не запущена!"
fi

echo ""
echo "========== Готово =========="
echo "Якщо bot-public не запущений або клони EXPIRED — перезапустіть:"
echo "  pkill -f 'python3 -m bot_public.main'; sleep 2"
echo "  screen -dmS bot-public bash -c 'cd $(pwd) && source venv/bin/activate && set -a && source .env.public && set +a && python3 -m bot_public.main'"
