#!/usr/bin/env bash
set -euo pipefail

test -f .env
docker compose config >/dev/null
docker compose build backend worker
docker compose up -d postgres redis qdrant
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
docker compose ps
