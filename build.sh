#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies for parselmouth
apt-get update
apt-get install -y build-essential libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0 ffmpeg libav-tools

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads
mkdir -p static
mkdir -p templates 