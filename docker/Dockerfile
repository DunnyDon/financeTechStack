# Multi-stage Dockerfile for Finance TechStack
# Stage 1: Builder - prepares dependencies
FROM python:3.13-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./

# Install dependencies using pip directly
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    prefect>=3.6.4 \
    requests>=2.31.0 \
    beautifulsoup4>=4.12.0 \
    lxml>=4.9.0 \
    pandas>=2.0.0 \
    pyarrow>=14.0.0 \
    python-dotenv>=1.0.0 \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0

# Stage 2: Runtime - minimal production image
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/db /app/logs && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser config.csv.template ./

# Copy optional files if they exist
COPY --chown=appuser:appuser README.md* ./uv.lock* ./

# Create placeholder for config
RUN cp config.csv.template config.csv && \
    chown appuser:appuser config.csv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PREFECT_API_URL=${PREFECT_API_URL:-http://prefect-server:4200/api} \
    PREFECT_HOME=/app/.prefect

# Create directories for Prefect and data
RUN mkdir -p /app/.prefect /app/db && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from src.main import aggregate_financial_data; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "prefect.cli", "server", "start", "--host", "0.0.0.0"]

# Labels for metadata
LABEL org.opencontainers.image.title="Finance TechStack" \
      org.opencontainers.image.description="SEC Filings & Financial Data Aggregation with Prefect" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.url="https://github.com/DunnyDon/financeTechStack"
