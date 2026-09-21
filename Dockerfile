# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    REST_API_HOST=0.0.0.0 \
    REST_API_PORT=8080

WORKDIR /app

# Install dependencies first so this layer is cached until requirements change.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code.
COPY app ./app

# Run as a non-root user.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8080

# Default config uses the mocked in-memory backend (STORAGE_TYPE=memory), so the
# container runs with zero external infrastructure. To use PostgreSQL, pass:
#   -e STORAGE_TYPE=postgres -e DB_HOST=... -e DB_USER=... -e DB_PASSWORD=... -e DB_NAME=...
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
