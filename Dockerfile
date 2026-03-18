FROM python:3.11-slim as base

# Add metadata
LABEL maintainer="CYBERBULL123"
LABEL description="ADgents - Autonomous Agent Platform"

# Setup environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (caching optimization)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source code
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data/db /app/data/files /app/data/agents

# Expose the API port
EXPOSE 8000

# Run the platform via start script
CMD ["python", "start.py"]
