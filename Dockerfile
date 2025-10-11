FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application

# Copy application
COPY . /app

# Ensure a non-root user and make /app writable
RUN useradd -m appuser || true \
    && chown -R appuser:appuser /app \
    && touch /app/clients.db \
    && chown appuser:appuser /app/clients.db

# Run as non-root user
USER appuser

EXPOSE 5000

ENV FLASK_APP=app.py

# Use eventlet as the async worker for SocketIO
CMD ["python", "app.py"]
