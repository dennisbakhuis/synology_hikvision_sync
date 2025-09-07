# Multi-stage build for smaller production image
# Stage 1: Build dependencies and install packages
FROM python:3.13-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    linux-headers \
    gcc \
    musl-dev \
    libffi-dev

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies into virtual environment
RUN uv pip install --no-cache-dir -e .

# Stage 2: Runtime image
FROM python:3.13-alpine AS runtime

# Set working directory
WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apk add --no-cache \
    libgcc \
    libstdc++ \
    dcron \
    && rm -rf /var/cache/apk/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy source code and entrypoint script
COPY src/ ./src/
COPY entrypoint.sh ./entrypoint.sh

# Create necessary directories
RUN mkdir -p /input /output /tmp/hikvision_cache

# Environment variables for configuration
ENV CAMERA_TRANSLATION="" \
    CACHE_DIR="/tmp/hikvision_cache" \
    LOCK_FILE="/tmp/process_hikvision_folder.lock" \
    RETENTION_DAYS="90" \
    CRON_INTERVAL="10" \
    RUN_MODE="cron" \
    PYTHONPATH="/app" \
    PATH="/opt/venv/bin:$PATH"

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Health check to ensure the application can start
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); import process_hikvision_folder; print('OK')" || exit 1

# Default entrypoint
ENTRYPOINT ["./entrypoint.sh"]