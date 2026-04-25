# syntax=docker/dockerfile:1.7
# ---------- Builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-deps . && \
    pip install --prefix=/install \
        "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" \
        "pydantic>=2.9.0" "pydantic-settings>=2.6.0" \
        "asyncpg>=0.30.0" "sqlalchemy[asyncio]>=2.0.36" "alembic>=1.14.0" \
        "redis[hiredis]>=5.2.0" \
        "python-jose[cryptography]>=3.3.0" "cryptography>=43.0.0" \
        "email-validator>=2.2.0" "httpx>=0.27.2" "jinja2>=3.1.4" \
        "structlog>=24.4.0" "prometheus-client>=0.21.0" \
        "python-multipart>=0.0.12"

# ---------- Runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages:/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

COPY --from=builder /install /install

WORKDIR /app
COPY app /app/app
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts

RUN chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
