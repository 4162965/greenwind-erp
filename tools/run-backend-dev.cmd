@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%\backend"
if not exist ".venv\Scripts\python.exe" (
  echo Backend virtual environment is missing.
  echo Please run start-local-dev.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.seed
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
pause
