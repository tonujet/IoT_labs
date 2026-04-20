@echo off
echo ============================================
echo   IoT Road Vision - Starting Full Stack
echo ============================================
echo.

echo [1/3] Starting Docker services...
docker compose up -d --build
if %errorlevel% neq 0 (
    echo ERROR: Docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)

echo.
echo [2/3] Waiting for Store API to be ready...
:wait_store
curl -s http://localhost:8000/processed_agent_data/ >nul 2>&1
if %errorlevel% neq 0 (
    echo     Waiting...
    timeout /t 2 /nobreak >nul
    goto wait_store
)
echo     Store API is ready!

echo.
echo     Grafana is available at http://localhost:3000 (admin/admin)
echo.
echo [3/3] Starting MapView desktop app...
echo     (Close the MapView window to stop the app)
echo.
cd MapView
python main.py

echo.
echo MapView closed. Docker services are still running.
echo To stop everything: docker compose down
pause
