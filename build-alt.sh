#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

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

echo "System dependencies installed"

# Upgrade pip and install build tools first
python -m pip install --upgrade pip setuptools wheel

echo "Build tools upgraded"

# Try to install parselmouth separately first
echo "Installing parselmouth..."
pip install parselmouth==1.1.1 || {
    echo "Failed to install parselmouth, trying alternative approach..."
    pip install --no-deps parselmouth==1.1.1 || {
        echo "Skipping parselmouth for now..."
    }
}

# Install other Python dependencies
echo "Installing other dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads
mkdir -p static
mkdir -p templates

echo "Build completed successfully" 