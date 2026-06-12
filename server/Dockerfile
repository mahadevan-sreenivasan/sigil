FROM python:3.13-slim AS builder

WORKDIR /build

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install .


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ src/
COPY migrations/ migrations/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["uvicorn", "sigil_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
