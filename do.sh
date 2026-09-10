#!/usr/bin/env bash
# Helper de comenzi frecvente pentru Vocal Separator.
# Ruleaza din radacina repo-ului: ./do.sh <comanda>
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/vocal-separator"

usage() {
  cat <<EOF
Utilizare: ./do.sh <comanda>

  up              Porneste tot stack-ul (docker compose up -d)
  down            Opreste tot stack-ul
  build           Rebuild toate imaginile (backend, celery, frontend)
  rebuild         build + up, pentru cand ai modificat cod
  logs [serviciu] Log-uri live (implicit: toate serviciile)
  test            Ruleaza suita completa de teste pytest
  test-file <f>   Ruleaza doar un fisier de test (ex: test_speed_adjuster.py)
  health          Verifica rapid ca backend/frontend/swagger raspund
  shell           Deschide un shell in containerul backend
  clean-outputs   Sterge fisierele din uploads/ si outputs/ (NU sterge codul)
EOF
}

case "${1:-}" in
  up)
    docker compose up -d
    ;;
  down)
    docker compose down
    ;;
  build)
    docker compose build backend celery frontend
    ;;
  rebuild)
    docker compose build backend celery frontend
    docker compose up -d backend celery frontend
    ;;
  logs)
    docker compose logs -f "${2:-}"
    ;;
  test)
    docker exec vocal_remover-backend-1 python3 -m pytest backend/ -v
    ;;
  test-file)
    if [ -z "${2:-}" ]; then echo "Specifica fisierul: ./do.sh test-file test_speed_adjuster.py"; exit 1; fi
    docker exec vocal_remover-backend-1 python3 -m pytest "backend/$2" -v
    ;;
  health)
    echo -n "Backend:    "; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/api/health
    echo -n "Frontend:   "; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3001
    echo -n "Swagger UI: "; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080
    ;;
  shell)
    docker exec -it vocal_remover-backend-1 /bin/sh
    ;;
  clean-outputs)
    read -p "Sigur stergi tot din uploads/ si outputs/? [y/N] " confirm
    if [ "$confirm" = "y" ]; then
      find backend/uploads -type f ! -name '.gitkeep' -delete
      find backend/outputs -mindepth 1 ! -name '.gitkeep' -delete
      echo "Curatat."
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
