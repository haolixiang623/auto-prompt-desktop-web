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

## Docker

Build:

```bash
docker build -t auto-prompt-web .
```

Run:

```bash
docker run --rm -p 3000:3000 -v "$(pwd)/.runtime-data:/data" auto-prompt-web
```

Quick container verification:

```bash
npm run docker:verify
```

## Notes

- The active server runtime is Python.
- Build and start commands now target the Python backend.
