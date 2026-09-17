# Linux VPS Deployment

The production target is a Linux VPS running Docker Compose. Local Phase 1
development remains native Python and does not require Docker.

## Services

`nginx`, `frontend`, `backend`, `worker`, `postgres`, `qdrant` and `redis` run
on a private Compose network. Only Nginx publishes ports 80 and 443. Persistent
volumes hold PostgreSQL, Qdrant and Redis data.

## First deployment

```bash
cp deploy/.env.production.example .env
# replace POSTGRES_PASSWORD and provider secrets
docker compose config
docker compose up -d --build
docker compose ps
```

The backend health check is `GET /health`. Nginx routes `/api/` to FastAPI and
all other paths to the Next.js frontend. The worker consumes Redis jobs through
ARQ and uses the same LangGraph deep-research workflow.

## Yahoo through the VPS Xray node

Set `YAHOO_PROXY_URL=http://host.docker.internal:10811` when Yahoo requests
must use the VPS Xray HTTP inbound. The backend and worker map
`host.docker.internal` to the Docker host. The Xray inbound must accept the
Docker bridge gateway (not only `127.0.0.1`); keep ports 10811/10812 blocked
from the public Internet with the VPS firewall.

## HTTPS with Let's Encrypt

Point DNS at the VPS, set the real `server_name` in `nginx/nginx.conf`, and
bootstrap the certificate with Certbot using the mounted
`deploy/certbot/www` and `deploy/certbot/conf` paths. After issuance, add a
port-443 server block that redirects port 80 to HTTPS and references the
certificate files. Renew with a scheduled `certbot renew` followed by
`docker compose exec nginx nginx -s reload`.

## Operations

- Keep `.env` outside Git and rotate credentials independently.
- Keep PostgreSQL, Redis and Qdrant unexposed to the Internet.
- Run `deploy/backup.sh` on a schedule and copy archives off-host.
- Inspect `docker compose logs --tail=200 backend worker nginx` after deploy.
- Use restart policies and health checks before accepting traffic.

Docker CLI was not available in the Windows development environment during
Phase 9, so `docker compose config/build` must be run on the target Linux VPS.
