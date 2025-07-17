#!/usr/bin/env bash
set -e

# Install necessary dependencies for Chromium
apt-get update && apt-get install -y \
    curl \
    gnupg \
    unzip \
    wget \
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
    fonts-noto-color-emoji \
    lsb-release \
    software-properties-common

# Install Python requirements
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variable for playwright browser path
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

# Install Chromium for Playwright (must be last)
npx playwright install chromium
