#!/usr/bin/env bash
# Запуск основного бота (для власного використання, без підписки за замовчуванням)
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "Створіть .env з .env.example"
  exit 1
fi

export DATABASE_PATH="${DATABASE_PATH:-bot.db}"

if [ -d venv ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec python3 -m bot.main
