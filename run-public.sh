#!/usr/bin/env bash
# Запуск публічного бота (окрема копія для користувачів)
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env.public ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.public
  set +a
elif [ -f .env ]; then
  echo "Увага: використовується .env — краще створити .env.public"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "Створіть .env.public з .env.public.example"
  exit 1
fi

export DATABASE_PATH="${DATABASE_PATH:-bot_public.db}"

if [ -d venv ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec python3 -m bot_public.main
