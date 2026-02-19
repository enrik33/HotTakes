# HotTakes - Download and Setup Guide

Use this guide when cloning or downloading the repository fresh.

## 1. Get the Repository

```powershell
git clone https://github.com/enrik33/HotTakes.git
cd HotTakes
```

## 2. Bootstrap Missing MVP Stubs (Optional but Recommended)

```powershell
powershell -ExecutionPolicy Bypass -File .\STARTER_BOOTSTRAP.ps1
```

## 3. Configure Backend Environment

```powershell
Copy-Item backend/.env.example backend/.env
# Edit backend/.env with Reddit credentials and DB values
```

## 4. Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

## 5. Run API

```powershell
cd backend
uvicorn app.main:app --reload
```

Open:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## 6. Optional Docker Run

```powershell
docker-compose up --build
```

## Notes

- This MVP is Reddit-only ingestion but schema is platform-ready.
- Main scope and rules are in `PROJECT_SPECIFICATION.md`.
