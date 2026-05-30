#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

cd "$ROOT_DIR"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T api python - <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

source = Path("/data/app.db")
backup_dir = Path("/data/backups")
backup_dir.mkdir(parents=True, exist_ok=True)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
target = backup_dir / f"app-{stamp}.sqlite3"

if not source.exists():
    raise SystemExit(f"SQLite database not found: {source}")

with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)

print(target)
PY
