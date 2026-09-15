#!/usr/bin/env bash
set -euo pipefail

test -f .env
docker compose config >/dev/null
docker compose up -d --build
docker compose ps
