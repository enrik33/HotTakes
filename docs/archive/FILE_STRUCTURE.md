# HotTakes - File Structure

```text
HotTakes/
  README.md
  SETUP_README.md
  PROJECT_SPECIFICATION.md
  PHASE_0_CHECKLIST.md
  STARTER_BOOTSTRAP.ps1
  docker-compose.yml

  backend/
    Dockerfile
    requirements.txt
    .env.example
    app/
      __init__.py
      main.py
      config.py
      database.py
      models.py
      routes/
        __init__.py
        health.py
        topics.py
        comments.py
        clusters.py
        timeline.py
      tasks/
        __init__.py
        scheduler.py
      services/
        __init__.py
      schemas/
        __init__.py
    tests/
      __init__.py

  frontend/
  docs/
```

## Notes

- Backend import root is `app` when running from `backend/`.
- Start API from `backend/` with `uvicorn app.main:app --reload`.
- Additional service/task starter files can be generated with `STARTER_BOOTSTRAP.ps1`.
