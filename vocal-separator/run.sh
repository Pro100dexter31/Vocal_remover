#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"

log() { printf '\n[%s] %s\n' "Vocal Separator" "$1"; }

check_command() {
  command -v "$1" >/dev/null 2>&1 || { printf 'Missing required command: %s\n' "$1" >&2; exit 1; }
}

setup_backend() {
  check_command python3
  [[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -r "$BACKEND_DIR/requirements.txt"
  [[ -f "$BACKEND_DIR/.env" ]] || cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
}

setup_frontend() {
  check_command node
  check_command npm
  (cd "$FRONTEND_DIR" && npm install)
}

run_redis() {
  if command -v docker >/dev/null 2>&1; then
    docker compose up redis
  else
    check_command redis-server
    redis-server
  fi
}

run_backend() {
  setup_backend
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  cd "$ROOT_DIR"
  python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
}

run_celery() {
  setup_backend
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  cd "$ROOT_DIR"
  celery -A backend.tasks worker --loglevel=info
}

run_frontend() {
  setup_frontend
  cd "$FRONTEND_DIR"
  npm start
}

run_all() {
  setup_backend
  setup_frontend
  if command -v docker >/dev/null 2>&1; then
    docker compose up --build
    return
  fi
  check_command redis-server
  redis-server >"$ROOT_DIR/redis.log" 2>&1 & REDIS_PID=$!
  trap 'kill "$REDIS_PID" "$CELERY_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' EXIT INT TERM
  run_celery >"$ROOT_DIR/celery.log" 2>&1 & CELERY_PID=$!
  run_backend >"$ROOT_DIR/backend.log" 2>&1 & BACKEND_PID=$!
  run_frontend >"$ROOT_DIR/frontend.log" 2>&1 & FRONTEND_PID=$!
  wait
}

case "${1:-run-all}" in
  run-all) run_all ;;
  run-backend) run_backend ;;
  run-frontend) run_frontend ;;
  run-redis) run_redis ;;
  run-celery) run_celery ;;
  setup) setup_backend; setup_frontend ;;
  *) printf 'Usage: %s {run-all|run-backend|run-frontend|run-redis|run-celery|setup}\n' "$0"; exit 2 ;;
esac
