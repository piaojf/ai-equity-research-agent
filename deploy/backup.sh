#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-equity}" "${POSTGRES_DB:-equity}" \
  | gzip > "backups/equity-$(date +%Y%m%d-%H%M%S).sql.gz"
