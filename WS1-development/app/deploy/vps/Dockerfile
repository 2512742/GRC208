# RiskTrack for the shared VPS (see deploy/vps/README.md).
# Stage 1 builds the React app; stage 2 is the API, which also serves that build.

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN useradd --system --uid 10001 --create-home risktrack
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./
COPY sample_data/ /app/sample_data/
COPY --from=web /web/dist /app/frontend/dist
# The SQLite file lives in a named volume mounted here; the app runs unprivileged.
RUN mkdir -p /app/backend/data && chown -R risktrack:risktrack /app/backend/data
USER risktrack
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4).status == 200 else 1)"
# Migrations first (single instance, SQLite), then one worker: SQLite has one writer anyway.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1 --proxy-headers --forwarded-allow-ips '*' --no-server-header"]
