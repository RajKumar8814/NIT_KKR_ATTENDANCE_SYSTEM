# Use official lightweight Python image
FROM python:3.10-slim

# Set Python behavior rules
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Linux system dependencies necessary to compile dlib and support face_recognition
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set backend working directory
WORKDIR /app

# Upgrade pip explicitly
RUN pip install --no-cache-dir --upgrade pip

# Pre-Install cmake so dlib detects it perfectly during its build phase
RUN pip install --no-cache-dir cmake

# Copy requirements explicitly to cache dependency layers efficiently
COPY requirements.txt .

# Install dlib first, then everything else from requirements
RUN pip install --no-cache-dir dlib && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files (templates, static, routing, etc.)
COPY . .

# Expose Railway's dynamic port (defaults to 5000 if testing locally)
ENV PORT=5000
EXPOSE $PORT

# Run Gunicorn with extreme memory profiling matching the 512MB RAM free tier limit
CMD ["sh", "-c", "gunicorn --workers 1 --threads 2 --timeout 180 --bind 0.0.0.0:$PORT app:app"]
