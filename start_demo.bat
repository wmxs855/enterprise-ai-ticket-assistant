@echo off
cd /d "%~dp0"
echo Starting the local demo at http://127.0.0.1:8000/
".venv\Scripts\python.exe" -B -X utf8 -m uvicorn src.api:app --host 127.0.0.1 --port 8000
pause
