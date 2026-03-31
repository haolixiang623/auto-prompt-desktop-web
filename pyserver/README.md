# Python Backend

This directory contains the active backend for Auto-Prompt.

## Run

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

## Notes

- The backend is FastAPI-based.
- Static frontend assets are served from the root `dist/` directory.
- Skills are executed from the repository `skills/` directory.
