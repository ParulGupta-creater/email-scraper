#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

# Update and install essential tools
apt-get update && apt-get install -y \
  ca-certificates \
  curl \
  dnsutils \
  net-tools \
  iputils-ping \
  lsb-release \
  gnupg \
  software-properties-common

# Optional DNS debug
dig example.com || true

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Explicitly set Playwright cache path and install browsers
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright
playwright install --with-deps
