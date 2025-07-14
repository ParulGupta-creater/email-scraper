#!/usr/bin/env bash

# Exit immediately on any error
set -e

# Update system tools and install required utilities
apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    wget \
    gnupg \
    software-properties-common \
    dnsutils \
    net-tools \
    iputils-ping \
    lsb-release

# Optional: confirm DNS works
dig example.com || true

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install --with-deps
