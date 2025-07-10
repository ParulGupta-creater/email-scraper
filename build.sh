#!/usr/bin/env bash

# Install dependencies
apt-get update && apt-get install -y wget unzip curl gnupg2 ca-certificates

# Install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install -y ./google-chrome-stable_current_amd64.deb || apt-get -f install -y

# Ensure Chrome installed
google-chrome --version

# Install pip dependencies
pip install -r requirements.txt
python --version
