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
    libffi-dev

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
    MAX_CONTENT_LENGTH=52428800 \
    PDF_EXPIRY_SECONDS=86400 \
    PERSISTENCE_ENABLED=true \
    PERSISTENCE_INTERVAL=60 \
    FLASK_DEBUG=0

# Copy wheels from builder stage and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Install runtime dependencies only
RUN apk add --no-cache \
    libjpeg \
    zlib \
    openssl \
    wget \
    curl

# Create necessary directories with proper permissions
RUN mkdir -p /app/static/uploads \
    /app/static/output \
    /app/templates \
    /app/frontend \
    /app/data

# Add a non-root user to run the application
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy application code
COPY pdfMergerWebsite/ /app/

# Set ownership of application files and directories
RUN chown -R appuser:appgroup /app

# Set appropriate permissions
RUN chmod -R 755 /app && \
    chmod -R 775 /app/static/uploads /app/static/output /app/data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Verify template and static directories
RUN ls -la /app/templates || echo "Warning: templates directory empty" && \
    ls -la /app/static || echo "Warning: static directory empty" && \
    ls -la /app/frontend || echo "Warning: frontend directory empty"

# Add health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Command to run the application with production server
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers=$(( 2 * $(nproc) + 1 )) --timeout=120 --log-level=$LOG_LEVEL server:app"]