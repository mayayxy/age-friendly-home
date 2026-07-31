@echo off
cd /d %~dp0
if not exist .env (
  echo 请先复制 .env.example 为 .env，并填入 VISION_API_KEY
  pause
  exit /b 1
)
python -m uvicorn server:app --host 0.0.0.0 --port 8000
