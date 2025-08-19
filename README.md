# Dispatcher Monorepo
Frontend: Next.js 14 (Vercel-ready)  
Backend: FastAPI (Railway/Timeweb-ready)  
DB: PostgreSQL (TimewebCloud)

## Быстрый старт
1) Примените SQL в БД: `backend/db.sql` (схема), затем `backend/extras.sql` (триггеры/поиск).
2) Backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   # Windows: setx DATABASE_URL "postgresql://user:pass@host:5432/dispatcher"
   # Linux/Mac: export DATABASE_URL="..."
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3) Frontend:
   ```bash
   cd frontend
   cp .env.example .env.local # укажите NEXT_PUBLIC_API_URL
   npm install
   npm run dev
   ```

## Деплой
- Backend → Railway: корень = `backend/`, переменные: `DATABASE_URL`, `CORS_ORIGINS`.
- Frontend → Vercel: корень = `frontend/`, переменная: `NEXT_PUBLIC_API_URL` (URL бэка). 