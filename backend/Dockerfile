FROM python:3.14-slim-bookworm as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ /app/src/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir ".[dev]"

# Production image
FROM python:3.14-slim-bookworm

WORKDIR /app

# Install runtime dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN useradd --create-home --shell /bin/bash sensei && \
    chown -R sensei:sensei /app
USER sensei

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini as init process for proper signal handling (SIGTERM → graceful shutdown)
ENTRYPOINT ["tini", "--"]

# Run the application with Gunicorn (multi-worker for concurrency)
# --graceful-timeout: time to finish in-flight requests on SIGTERM
# --max-requests/--max-requests-jitter: recycle workers to prevent memory leaks
# --backlog: connection queue size for burst traffic
CMD ["/bin/sh", "-c", "gunicorn sensei.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-4} --timeout ${WORKER_TIMEOUT:-120} --graceful-timeout ${GRACEFUL_TIMEOUT:-30} --keep-alive ${KEEP_ALIVE:-5} --max-requests ${MAX_REQUESTS:-10000} --max-requests-jitter ${MAX_REQUESTS_JITTER:-1000} --backlog ${BACKLOG:-2048} --log-level info --access-logfile - --error-logfile -"]
