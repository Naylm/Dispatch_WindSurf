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
# Workers configuration: use environment variable or default to 4
# Note: eventlet provides async I/O via greenlets, workers provide parallelism
CMD gunicorn --worker-class eventlet -w ${GUNICORN_WORKERS:-4} --bind 0.0.0.0:5000 app:app
