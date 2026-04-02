#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Starting Build Process ---"

# 1. Update and install system dependencies for dlib/face-recognition
# We include build-essential to ensure the C++ compiler is ready
apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libboost-all-dev \
    libgl1-mesa-glx

echo "--- System Dependencies Installed ---"

# 2. Upgrade pip to ensure the latest wheel support
pip install --upgrade pip

# 3. Install Python requirements
# This step will take 10-15 minutes because it compiles 'dlib'
pip install -r requirements.txt

echo "--- Build Finished Successfully ---"