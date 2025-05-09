# Multi-stage build for optimized production image

# Build stage
FROM python:3.13-alpine AS builder

WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    libressl-dev \
    libffi-dev  # Required for some cryptography packages

# Build wheels for dependencies
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Final stage
FROM python:3.13-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    LOG_LEVEL=INFO \
    MAX_CONTENT_LENGTH=16777216 \
    FLASK_ENV=production

# Copy wheels from builder stage and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Install runtime dependencies only
RUN apk add --no-cache \
    libjpeg \
    zlib \
    openssl \
    wget

# Create necessary directories first
RUN mkdir -p /app/static/uploads /app/static/output /app/templates /app/frontend

# Copy application code - be more specific about what's being copied
COPY pdfMergerWebsite/server.py /app/
COPY pdfMergerWebsite/backend/ /app/backend/
COPY pdfMergerWebsite/frontend/ /app/frontend/
COPY pdfMergerWebsite/templates/ /app/templates/

# Add a non-root user to run the application
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Set ownership of application files
RUN chown -R appuser:appgroup /app

# Set appropriate permissions
RUN chmod -R 755 . && \
    chmod -R 775 static/uploads static/output

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Add health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

# Command to run the application with production server
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers=$(( 2 * $(nproc) + 1 )) --timeout=120 --log-level=$LOG_LEVEL server:app"]