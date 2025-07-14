#!/usr/bin/env bash

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install --with-deps
#!/usr/bin/env bash

# Update system packages and install CA certificates & network tools
apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    dnsutils \
    net-tools \
    iputils-ping \
    lsb-release \
    gnupg \
    software-properties-common

# Optional: confirm DNS resolution inside build
dig example.com || true

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
