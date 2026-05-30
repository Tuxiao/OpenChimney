#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not in PATH" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE" >&2
  echo "Create it first: cp .env.docker.example .env" >&2
  exit 1
fi

cd "$ROOT_DIR"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
