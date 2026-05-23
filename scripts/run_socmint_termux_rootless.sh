#!/usr/bin/env bash
# Rootless Termux SOCMINT v10.32 Hidden Service Setup

# Update Termux and install packages
pkg update -y && pkg upgrade -y
pkg install -y python git curl

# Clone SOCMINT repository and checkout v10.32 branch
git clone https://github.com/pmwensing/SOCMINT-PROJECT.git ~/SOCMINT-PROJECT
cd ~/SOCMINT-PROJECT
git checkout feat/v10.32-productization-ux

# Install Python dependencies
pip install --no-cache-dir flask pytest

# Run SOCMINT v10.32 directly as a hidden Flask service
export FLASK_APP=src/socmint/v10_32_productization_ux_routes.py
flask run --host=127.0.0.1 --port=5000

# Access endpoints locally
echo "SOCMINT v10.32 hidden service is running on http://127.0.0.1:5000"
echo "Use curl or browser on your device via localhost or SSH tunnel to access endpoints."