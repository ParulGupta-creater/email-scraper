#!/usr/bin/env bash
set -e

# Install necessary system packages for Chromium
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
    fonts-noto-color-emoji

# Upgrade pip and install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# ✅ Install Playwright browsers locally to avoid shared cache issues
export PLAYWRIGHT_BROWSERS_PATH=0
playwright install --with-deps chromium
