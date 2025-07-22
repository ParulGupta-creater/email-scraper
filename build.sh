#!/usr/bin/env bash
set -e

# Optional: update packages (minimal for Python and networking)
apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    unzip

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
