# Phase 0: Setup Checklist

Complete these steps before starting Phase 1 (Data Pipeline).

**Estimated Time:** 2–4 hours

---

## GitHub & Repository

- [ ] Create GitHub repository: `social-debate-analyzer`
- [ ] Clone to local machine
- [ ] Create directory structure:
  ```
  social-debate-analyzer/
  ├── backend/
  │   ├── app/
  │   │   ├── models/
  │   │   ├── routes/
  │   │   ├── services/
  │   │   └── tasks/
  │   ├── tests/
  │   └── migrations/
  ├── frontend/
  │   └── src/
  │       ├── components/
  │       ├── pages/
  │       └── api/
  └── docs/
  ```
- [ ] Create `.gitignore`
  ```
  venv/
  .env
  *.db
  __pycache__/
  .pytest_cache/
  node_modules/
  dist/
  .DS_Store
  ```

---

## Backend Setup

### Python & Virtual Environment

- [ ] Verify Python 3.10+ installed: `python --version`
- [ ] Navigate to `backend/`
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate:
  - macOS/Linux: `source venv/bin/activate`
  - Windows: `venv\Scripts\activate`
- [ ] Upgrade pip: `pip install --upgrade pip`

### Dependencies

- [ ] Copy `requirements.txt` to `backend/`
- [ ] Install: `pip install -r requirements.txt`
- [ ] Verify key packages:
  ```bash
  python -c "import fastapi; import praw; import sqlalchemy; print('OK')"
  ```

### Configuration

- [ ] Copy `app/main.py`, `app/config.py`, `app/database.py`, `app/models.py`
- [ ] Create `app/routes/__init__.py` (empty file)
- [ ] Create `app/services/__init__.py` (empty file)
- [ ] Create `app/tasks/__init__.py` (empty file)
- [ ] Copy route files to `app/routes/`
- [ ] Copy scheduler to `app/tasks/`
- [ ] Copy `.env.example` to `.env.example`
- [ ] Create `.env` by copying `.env.example`:
  ```bash
  cp .env.example .env
  ```

### Reddit API Credentials

*You'll need to register your app on Reddit to get credentials.*

1. Go to https://www.reddit.com/prefs/apps
2. Click "are you a developer? create an app..."
3. Fill in:
   - **name:** Social Debate Analyzer
   - **app type:** script
   - **description:** Data collection tool
4. Get your:
   - **CLIENT_ID** (shown under "personal use script")
   - **CLIENT_SECRET**
5. Edit `.env` and fill in:
   ```env
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=SocialDebateAnalyzer/1.0 (by u/your_username)
   REDDIT_USERNAME=your_reddit_username
   REDDIT_PASSWORD=your_reddit_password
   ```

### Database

- [ ] Decide on database:
  - **Dev (quick):** SQLite — no setup needed
  - **Dev (closer to prod):** PostgreSQL 14+
- [ ] If using SQLite:
  - Update `.env`: `DATABASE_URL=sqlite:///./social_debate.db`
  - Database auto-created on first run
- [ ] If using PostgreSQL:
  - Install PostgreSQL locally or use Docker + docker-compose
  - Create database: `createdb social_debate`
  - Update `.env`: `DATABASE_URL=postgresql://user:password@localhost/social_debate`

### Test Backend

- [ ] Start FastAPI: `uvicorn app.main:app --reload`
- [ ] Verify at http://localhost:8000
  - Root endpoint: `/`
  - Health check: `/health`
  - Docs: `/docs` (interactive Swagger UI)
- [ ] Check database connection in `/health` response
- [ ] Stop server: `Ctrl+C`

---

## Frontend Setup

### Node.js

- [ ] Verify Node.js 18+ installed: `node --version`
- [ ] Verify npm installed: `npm --version`

### Create React App

- [ ] Navigate to `frontend/`
- [ ] Initialize React + Vite:
  ```bash
  npm create vite@latest . -- --template react-ts
  ```
- [ ] Or install manually:
  ```bash
  npm install react@18 react-dom@18
  npm install -D vite @vitejs/plugin-react typescript
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```

### Dependencies

- [ ] Install core dependencies:
  ```bash
  npm install axios react-router-dom plotly.js
  npm install -D tailwindcss postcss autoprefixer
  ```

### Configuration

- [ ] Create `.env` in `frontend/`:
  ```env
  VITE_API_BASE_URL=http://localhost:8000
  ```
- [ ] Update `package.json` to add dev server on port 5173

### Test Frontend

- [ ] Start dev server: `npm run dev`
- [ ] Verify at http://localhost:5173
- [ ] Check console for errors
- [ ] Stop server: `Ctrl+C`

---

## Docker (Optional but Recommended)

### Setup

- [ ] Copy `docker-compose.yml` to root
- [ ] Copy `Dockerfile` to `backend/`
- [ ] Verify Docker & Docker Compose installed:
  ```bash
  docker --version
  docker-compose --version
  ```

### Test

- [ ] Build images: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Test endpoints:
  - API: http://localhost:8000/health
  - Frontend: http://localhost:5173
  - Docs: http://localhost:8000/docs
- [ ] Stop services: `docker-compose down`

---

## Project Documentation

- [ ] Copy `PROJECT_SPECIFICATION.md` to root
- [ ] Copy `SETUP_README.md` to root (or rename to `README.md`)
- [ ] Copy `FILES_SUMMARY.md` to root/docs
- [ ] Copy this checklist to root/docs

---

## Git Commit

- [ ] Stage all files: `git add .`
- [ ] Commit: `git commit -m "Phase 0: Initial project setup with bootstrap code"`
- [ ] Push: `git push origin main` (if using GitHub)

---

## Verification Checklist

Run through these before starting Phase 1:

- [ ] Backend hello world works: `GET http://localhost:8000/`
- [ ] Health check works: `GET http://localhost:8000/health`
- [ ] Swagger docs available: `GET http://localhost:8000/docs`
- [ ] Database connects (SQLite or PostgreSQL)
- [ ] Frontend loads: `http://localhost:5173`
- [ ] `.env` is filled with Reddit credentials
- [ ] All files in `PROJECT_SPECIFICATION.md` match your setup
- [ ] Python dependencies installed: `pip list | grep fastapi`
- [ ] Node dependencies installed: `npm list react`
- [ ] Git repo initialized and first commit made

---

## Troubleshooting Phase 0

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -r requirements.txt` in activated venv |
| Port 8000 already in use | `lsof -i :8000` (mac/linux) or find process and kill it |
| `psycopg2` import error with PostgreSQL | `pip install psycopg2-binary` |
| Reddit credentials 401 error | Verify CLIENT_ID and CLIENT_SECRET, check app isn't suspended |
| CORS error on frontend | Ensure `CORS_ORIGINS` in `app/config.py` includes frontend URL |
| Docker fails to build | Check `requirements.txt` syntax, verify Docker is running |
| Node version mismatch | Install nvm (node version manager) and use Node 18+ |

---

## Next Steps (After Phase 0)

Once everything is running, start **Phase 1: Data Pipeline**

See `PROJECT_SPECIFICATION.md` → "Implementation Phases" → "Phase 1: Data Pipeline (Days 1–3)"

Key task: Implement `services/reddit_fetcher.py` using PRAW

---

**Status:** Phase 0 Checklist  
**Estimated Completion:** ~4 hours  
**Next:** Phase 1 Data Pipeline (Days 1–3)
