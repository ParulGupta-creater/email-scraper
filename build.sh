#!/usr/bin/env bash

apt-get update
apt-get install -y wget unzip gnupg curl

# Install Google Chrome for headless browsing
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install ./google-chrome-stable_current_amd64.deb -y
