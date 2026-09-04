# Use an official Python compact runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set the working directory
WORKDIR /app

# Install necessary system dependencies for psycopg2 and light build tasks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the Render-specific (production CPU-only) dependencies
COPY requirements.render.txt .

# Install dependencies (utilizing PyTorch CPU wheel cache from requirements)
RUN pip install --no-cache-dir -r requirements.render.txt

# Copy the rest of the application code
COPY . .

# Expose the Cloud Run port
EXPOSE $PORT

# Command to run the application using Uvicorn
CMD ["sh", "-c", "uvicorn api_reference:app --host 0.0.0.0 --port ${PORT:-8080}"]
