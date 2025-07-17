#!/usr/bin/env bash
set -e

# Set environment variable to ensure consistent path
export PLAYWRIGHT_BROWSERS_PATH=0

# Install necessary system dependencies for Chromium
apt-get update && apt-get install -y \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    wget \
    gnupg \
    curl \
    unzip \
    lsb-release \
    fonts-noto-color-emoji \
    software-properties-common

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Force Playwright to install Chromium in project dir (PLAYWRIGHT_BROWSERS_PATH=0)
python -m playwright install chromium
