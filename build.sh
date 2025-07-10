#!/usr/bin/env bash

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install --with-deps
