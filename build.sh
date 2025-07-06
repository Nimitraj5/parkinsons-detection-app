#!/usr/bin/env bash
# exit on error
set -o errexit

# Update package lists
apt-get update

# Install system dependencies for parselmouth and audio processing
apt-get install -y \
    build-essential \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    libav-tools \
    python3-dev \
    pkg-config \
    libtool \
    autoconf \
    automake

# Upgrade pip and install build tools first
python -m pip install --upgrade pip setuptools wheel

# Try to install main requirements first
echo "Installing main requirements..."
if pip install -r requirements.txt; then
    echo "Main requirements installed successfully"
else
    echo "Main requirements failed, trying minimal requirements..."
    pip install -r requirements-minimal.txt
fi

# Create necessary directories
mkdir -p uploads
mkdir -p static
mkdir -p templates 