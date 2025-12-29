# CiteKit Backend - Cloud Run Dockerfile
# Optimized for production deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright and other packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for smaller image)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p /app/output

# Environment variables (will be overridden by Cloud Run)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the application
# Note: We use gunicorn with uvicorn workers for production
CMD exec gunicorn main:app \
    --bind :$PORT \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --keep-alive 5 \
    --log-level info
