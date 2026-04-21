# Auto-Prompt Web

`Auto-Prompt Web` is now wired around a Python backend (`FastAPI`) plus the existing Vue 3 frontend.

## Stack

- Frontend: Vue 3 + Vite
- Backend: Python + FastAPI
- Skills: Python scripts under `skills/`

## Active Layout

```text
auto-prompt-desktop-web/
├─ src/        # Vue frontend
├─ pyserver/   # Python backend
├─ skills/     # Python skills
├─ dist/       # Built frontend assets
└─ Dockerfile  # Python runtime image
```

## Local Run

Install frontend dependencies:

```bash
npm install
```

Install backend dependencies:

```bash
cd pyserver
pip install -r requirements.txt
```

Start frontend dev server:

```bash
npm run dev:web
```

Start backend:

```bash
npm run dev:server
```

If Python is not on `PATH`, set `AUTOPROMPT_PYTHON` to the full interpreter path first.

Default ports:

- Frontend: `http://127.0.0.1:1420`
- Backend: `http://127.0.0.1:3000`

## Build And Start

```bash
npm run build
npm run start
```

## Production Docker

The repository supports one Docker deployment path for production:
`Dockerfile` + `docker-compose.prod.yml`.

Start the full production stack locally:

```bash
npm run docker:up
```

Stop it:

```bash
npm run docker:down
```

The stack exposes the application at `http://127.0.0.1:8089`.

Quick container verification:

```bash
npm run docker:verify
```

## Notes

- The active server runtime is Python.
- Build and start commands now target the Python backend.
- Deprecated deployment scripts and alternate compose files have been removed in favor of the single production Docker path.
