FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libffi-dev \
    libssl-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories for persistence
RUN mkdir -p /app/data && \
    mkdir -p /app/static/uploads/wiki && \
    mkdir -p /app/static/uploads/avatars && \
    chmod -R 755 /app/static/uploads && \
    chmod -R 755 /app/data

# Declare volumes for persistence
VOLUME ["/app/data", "/app/static/uploads"]

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application with Gunicorn and eventlet
# Workers configuration: default 2 workers + async eventlet for realtime I/O
CMD gunicorn --worker-class eventlet -w ${GUNICORN_WORKERS:-2} --bind 0.0.0.0:5000 --timeout ${GUNICORN_TIMEOUT:-120} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} --keep-alive ${GUNICORN_KEEPALIVE:-65} app:app
