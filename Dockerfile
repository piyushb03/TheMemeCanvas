# =============================================================================
# TheMemeCanvas Automation Suite — Dockerfile
# =============================================================================
# Multi-stage build: Node (frontend) → Python (backend + bundled frontend)
# =============================================================================

# --------------------------------------------------------------------------
# Stage 1: Build React frontend
# --------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json ./
RUN npm install

# Build production bundle
COPY frontend/ ./
RUN npm run build

# --------------------------------------------------------------------------
# Stage 2: Python backend + bundled frontend
# --------------------------------------------------------------------------
FROM python:3.11-slim AS backend

# Install system dependencies (FFmpeg for thumbnail generation)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create required directories
RUN mkdir -p \
    logs \
    data \
    credentials \
    temp_downloads \
    temp_thumbnails \
    assets \
    assets/fonts

# Copy assets
COPY assets/ ./assets/

# Environment (overridden by docker-compose)
ENV APP_ENV=production
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV DATABASE_URL=sqlite:///./data/thememecanvas.db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
