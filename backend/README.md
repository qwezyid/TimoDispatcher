# Backend (FastAPI)

## Запуск
```bash
pip install -r requirements.txt
# Windows
setx DATABASE_URL "postgresql://dispatcher:password@db-host:5432/dispatcher"
setx CORS_ORIGINS "https://your-frontend.vercel.app,http://localhost:3000"
# Новый PowerShell
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Деплой Railway
Root Directory: backend/
Variables: DATABASE_URL, CORS_ORIGINS
Procfile уже добавлен.

## SQL
1) db.sql — базовая схема.
2) extras.sql — триггеры, аудит, поиск. 