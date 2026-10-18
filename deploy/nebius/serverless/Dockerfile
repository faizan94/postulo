# syntax=docker/dockerfile:1
# All-in-one image for Nebius Serverless AI: nginx (:8080) → Next + FastAPI.
# Browser hits one managed HTTPS URL; /api goes to the backend.

# ---- backend deps ----
FROM python:3.12-slim AS backend-deps
# Install uv via pip (COPY --from=ghcr.io/... breaks on some Docker Desktop / amd64 builds).
RUN pip install --no-cache-dir "uv==0.10.2"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/scripts ./scripts

# ---- frontend build (same-origin API via nginx) ----
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
FROM python:3.12-slim AS runtime
RUN apt-get update \
  && apt-get install -y --no-install-recommends nginx curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Node binary for Next.js standalone server
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules

WORKDIR /app
COPY --from=backend-deps /app/backend /app/backend
COPY --from=frontend-build /app/public /app/frontend/public
COPY --from=frontend-build /app/.next/standalone /app/frontend
COPY --from=frontend-build /app/.next/static /app/frontend/.next/static

COPY deploy/nebius/serverless/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nebius/serverless/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
  && mkdir -p /app/backend/data \
  && rm -f /etc/nginx/sites-enabled/default

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=127.0.0.1

EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=5 \
  CMD curl -sf http://127.0.0.1:8080/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
