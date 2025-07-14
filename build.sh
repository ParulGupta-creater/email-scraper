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

# Debug DNS (optional)
dig example.com || true

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser binaries (Chromium, etc.)
playwright install --with-deps
