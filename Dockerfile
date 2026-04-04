# Use official lightweight Python image compatible directly with specific ONNX bindings safely
FROM python:3.11-slim

# Set Python behavior rules
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Linux system dependencies necessary for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set backend working directory
WORKDIR /app

# Upgrade pip explicitly
RUN pip install --no-cache-dir --upgrade pip

# PRE-INSTALL PyTorch CPU exclusively to prevent Ultralytics from downloading the 2.5GB CUDA binaries
# This ensures the Docker image strictly remains under the 4.0 GB Railway free tier limit natively.
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy requirements explicitly to cache dependency layers efficiently
COPY requirements.txt .

# Install dependencies cleanly mapping pre-compiled wheels internally smoothly
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files (templates, static, routing, etc.)
COPY . .

# Expose Railway's dynamic port (defaults to 5000 if testing locally)
ENV PORT=5000
EXPOSE $PORT

# Run Gunicorn utilizing Async Uvicorn specifically hardcoding purely Single Core environments gracefully avoiding standard RAM deadlocks
# Run Gunicorn with gthread workers specifically for better handling of CPU-bound ML tasks and ensuring threads don't block the master.
CMD ["sh", "-c", "gunicorn app:app --worker-class gthread --workers 1 --threads 4 --timeout 180 --bind 0.0.0.0:$PORT"]
