@echo off
setlocal
cd /d "%~dp0"

"%~dp0tools\Python312\python.exe" -c "import celery, redis; print('Celery/Redis Python dependency: OK')"
if errorlevel 1 (
  echo Thieu dependency. Hay chay: tools\Python312\python.exe -m pip install "celery[redis]>=5.4.0"
  pause
  exit /b 1
)

"%~dp0tools\Python312\python.exe" -c "import redis; client=redis.Redis.from_url('redis://localhost:6379/0'); client.ping(); print('Redis localhost:6379: OK')"
if errorlevel 1 (
  echo Redis chua chay tai localhost:6379. Hay chay run_redis_docker.bat hoac bat Redis rieng.
  pause
  exit /b 1
)

echo Cau hinh Celery/Redis da san sang.
pause
