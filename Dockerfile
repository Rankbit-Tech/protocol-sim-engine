# Universal Simulation Engine - Industrial Protocol Simulation Platform
# Production-ready Docker image for multi-protocol industrial simulation

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build for production
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to not create virtual environment (we're already in container)
RUN poetry config virtualenvs.create false

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Install dependencies
RUN poetry install --only=main --no-root

# Copy default configuration
COPY config/default_config.yml ./config/default_config.yml

# Copy examples (optional - for reference)
COPY examples/ ./examples/

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create directory for user-provided configs
RUN mkdir -p /config

# Expose ports
# Modbus TCP default range
EXPOSE 15000-15010
# MQTT broker port
EXPOSE 1883
# OPC-UA default range
EXPOSE 4840-4850
# HTTP API
EXPOSE 8080

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 simulator
RUN chown -R simulator:simulator /app /config
USER simulator

# Use entrypoint script for config fallback logic
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD []

# Health check - verify API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/status', timeout=5)" || exit 1

# Labels for documentation
LABEL org.opencontainers.image.title="Universal Simulation Engine"
LABEL org.opencontainers.image.description="Multi-protocol industrial facility simulation platform with config-driven device deployment"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Universal Simulation Engine Team"
LABEL org.opencontainers.image.source="https://github.com/universal-simulation-engine/core"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.documentation="https://universal-simulation-engine.io/docs"
LABEL org.opencontainers.image.vendor="Universal Simulation Engine"
