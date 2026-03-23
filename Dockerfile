FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app

COPY package.json package-lock.json ./
COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src ./src

RUN npm ci
RUN npm run build

FROM rust:1-bookworm AS server-builder
WORKDIR /app

COPY server/Cargo.toml server/Cargo.toml
COPY server/src server/src

RUN cargo build --manifest-path server/Cargo.toml --release

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

ENV AUTO_PROMPT_REPO_ROOT=/app \
    AUTO_PROMPT_SKILLS_DIR=/app/skills \
    AUTO_PROMPT_WEB_DIST=/app/dist \
    AUTO_PROMPT_DATA_DIR=/data \
    PORT=3000 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN pip install openai openpyxl pymupdf

COPY --from=frontend-builder /app/dist /app/dist
COPY --from=server-builder /app/server/target/release/auto-prompt-web-server /usr/local/bin/auto-prompt-web-server
COPY skills /app/skills

VOLUME ["/data"]
EXPOSE 3000

CMD ["auto-prompt-web-server"]
