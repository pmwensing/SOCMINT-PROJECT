#!/usr/bin/env bash
# Termux SOCMINT v10.32 Hidden Service Setup

# Ensure Termux packages are installed
pkg update -y && pkg upgrade -y
pkg install -y git python docker

# Clone SOCMINT repo and checkout v10.32 branch
git clone https://github.com/pmwensing/SOCMINT-PROJECT.git ~/SOCMINT-PROJECT
cd ~/SOCMINT-PROJECT
git checkout feat/v10.32-productization-ux

# Build Docker image for hidden service
docker build -t socmint_v10_32_hidden .

# Run the hidden service (bind to localhost only)
docker run -d --name socmint_hidden -p 127.0.0.1:5000:5000 socmint_v10_32_hidden

# Access instructions
echo "SOCMINT v10.32 hidden service is running on http://127.0.0.1:5000"
echo "Use curl or browser on your device via localhost or SSH tunnel to access endpoints."