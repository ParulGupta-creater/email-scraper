#!/usr/bin/env bash

# Exit immediately on error
set -e

# System dependencies
apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    lsb-release \
    iputils-ping \
    dnsutils \
    net-tools \
    software-properties-common

# Confirm DNS works
dig example.com || true

# Upgrade pip & install project dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright and its browser binaries (CRITICAL)
python -m playwright install chromium --with-deps
