#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

# Update system and install required tools
apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    dnsutils \
    net-tools \
    iputils-ping \
    lsb-release \
    gnupg \
    software-properties-common

# Optional: Debug DNS resolution
dig example.com || true

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# ✅ Install Playwright browser (Chromium only) to the path Render expects
PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright \
  python -m playwright install chromium
