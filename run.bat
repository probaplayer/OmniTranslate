@echo off
setlocal

rem Everything below must run from the script's own directory: uvicorn needs
rem the repo root on sys.path to import the `server` package, and the
rem workspaces directory is resolved relative to the repo root.
cd /d "%~dp0"

set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Installing dependencies...
pip install -r "%~dp0requirements.txt" --quiet

rem Open the browser only once the server actually answers, otherwise a first
rem run (venv + pip install) lands the user on connection-refused. The poller
rem runs in the background so uvicorn stays in the foreground of this window,
rem where Ctrl+C still stops it.
echo Waiting for server, browser will open when ready...
start "" /b powershell -NoProfile -Command "for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:8000'; break } catch { Start-Sleep -Seconds 1 } }" >nul 2>&1

python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
