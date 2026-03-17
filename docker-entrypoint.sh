#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

echo "[entrypoint] waiting for MySQL and applying migrations..."
until alembic upgrade head; do
  echo "[entrypoint] MySQL not ready yet, retry in 3s"
  sleep 3
done

echo "[entrypoint] starting API"
exec uvicorn telegram_api_server.main:app --host 0.0.0.0 --port 8000
