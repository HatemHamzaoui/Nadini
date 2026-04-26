FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY pyproject.toml .
RUN pip install --prefix=/install --no-cache-dir .

FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /install /usr/local
WORKDIR /app
ENV PYTHONPATH=/app
COPY . .

# Whisper model cache
RUN mkdir -p /home/app/.cache && chown -R app:app /home/app /app
USER app

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--proxy-headers"]
