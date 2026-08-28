@echo off
setlocal

set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Installing dependencies...
pip install -r "%~dp0requirements.txt" --quiet

start "" http://127.0.0.1:8000

python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
