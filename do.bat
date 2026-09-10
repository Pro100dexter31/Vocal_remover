@echo off
REM Helper de comenzi frecvente pentru Vocal Separator (Windows).
REM Ruleaza din radacina repo-ului: do.bat <comanda>

cd /d "%~dp0vocal-separator"

if "%1"=="up" (
    docker compose up -d
) else if "%1"=="down" (
    docker compose down
) else if "%1"=="build" (
    docker compose build backend celery frontend
) else if "%1"=="rebuild" (
    docker compose build backend celery frontend
    docker compose up -d backend celery frontend
) else if "%1"=="logs" (
    docker compose logs -f %2
) else if "%1"=="test" (
    docker exec vocal_remover-backend-1 python3 -m pytest backend/ -v
) else if "%1"=="test-file" (
    docker exec vocal_remover-backend-1 python3 -m pytest backend/%2 -v
) else if "%1"=="health" (
    curl -s -o NUL -w "Backend:    HTTP %%{http_code}\n" http://localhost:8000/api/health
    curl -s -o NUL -w "Frontend:   HTTP %%{http_code}\n" http://localhost:3001
    curl -s -o NUL -w "Swagger UI: HTTP %%{http_code}\n" http://localhost:8080
) else if "%1"=="shell" (
    docker exec -it vocal_remover-backend-1 /bin/sh
) else (
    echo Utilizare: do.bat ^<comanda^>
    echo.
    echo   up              Porneste tot stack-ul
    echo   down            Opreste tot stack-ul
    echo   build           Rebuild toate imaginile
    echo   rebuild         build + up
    echo   logs [serviciu] Log-uri live
    echo   test            Ruleaza toate testele pytest
    echo   test-file ^<f^>   Ruleaza doar un fisier de test
    echo   health          Verifica backend/frontend/swagger
    echo   shell           Shell in containerul backend
)
