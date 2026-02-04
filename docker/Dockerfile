# Dockerfile optimise pour ShotURL v3.0 avec 4GB RAM
# Multi-stage build: Frontend React + Backend FastAPI + Playwright

# =============================================================================
# Stage 1: Build Frontend React
# =============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY web/package*.json ./

# Install ALL dependencies (needed for build)
RUN npm install

# Copy source
COPY web/ ./

# Build React app
RUN npm run build

# =============================================================================
# Stage 2: Production image avec FastAPI + Playwright
# =============================================================================
FROM python:3.11-slim

# Metadata
LABEL maintainer="SNF Security Team"
LABEL version="3.0.0"
LABEL description="ShotURL - Secure website screenshot & analysis tool"

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python deps
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user for security BEFORE installing Playwright
RUN useradd -m -u 1000 -s /bin/bash shoturl && \
    mkdir -p /app/logs && \
    chown -R shoturl:shoturl /app

# Force rebuild marker - updated 2026-01-20
ARG REBUILD_MARKER=2026-01-20

# Copy API code
COPY --chown=shoturl:shoturl api/ ./api/

# Copy built frontend from stage 1
COPY --chown=shoturl:shoturl --from=frontend-builder /app/frontend/dist ./web/dist/

# Switch to non-root user
USER shoturl

# Install Playwright browsers as shoturl user (after USER switch)
# Note: We already installed system dependencies above, so skip --with-deps
RUN playwright install chromium

# Environment variables for 4GB RAM optimization
ENV PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/shoturl/.cache/ms-playwright \
    MAX_CONCURRENT_BROWSERS=4 \
    MAX_MEMORY_MB=3500 \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
