# Lacuna - Privacy-aware data governance and lineage tracking
# Multi-stage build for efficient image size

# Build stage
FROM python:3.14-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./
COPY lacuna/__version__.py lacuna/

# Install dependencies
RUN pip install --no-cache-dir build wheel && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# Runtime stage
FROM python:3.14-slim as runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash lacuna

# Copy wheels and install
COPY --from=builder /app/wheels /app/wheels
RUN pip install --no-cache-dir /app/wheels/*.whl && \
    rm -rf /app/wheels

# Copy application code
COPY lacuna/ /app/lacuna/
COPY config/ /app/config/
COPY policies/ /app/policies/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/

# Set ownership
RUN chown -R lacuna:lacuna /app

USER lacuna

# Environment variables
ENV PYTHONPATH=/app
ENV LACUNA_CONFIG_PATH=/app/config

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run API server
EXPOSE 8000
CMD ["uvicorn", "lacuna.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

