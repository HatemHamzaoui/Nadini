FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --prefix=/install --no-cache-dir .

FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app

COPY --from=builder /install /usr/local
WORKDIR /app
ENV PYTHONPATH=/app
COPY . .

RUN chown -R app:app /app
USER app

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--proxy-headers"]
