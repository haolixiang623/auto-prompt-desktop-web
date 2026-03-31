FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app

COPY package.json package-lock.json ./
COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src ./src

RUN npm ci
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

ENV AUTO_PROMPT_REPO_ROOT=/app \
    AUTO_PROMPT_SKILLS_DIR=/app/skills \
    AUTO_PROMPT_WEB_DIST=/app/dist \
    AUTO_PROMPT_DATA_DIR=/data \
    PORT=3000 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyserver/requirements.txt /app/pyserver/requirements.txt
RUN pip install --no-cache-dir -r /app/pyserver/requirements.txt

COPY --from=frontend-builder /app/dist /app/dist
COPY pyserver /app/pyserver
COPY skills /app/skills

VOLUME ["/data"]
EXPOSE 3000

CMD ["python", "-m", "uvicorn", "pyserver.app.main:app", "--host", "0.0.0.0", "--port", "3000"]
