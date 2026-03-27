#!/bin/bash
# Configure Docker to use NVIDIA GPU runtime
set -e
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
echo "✓ Docker NVIDIA runtime configured and restarted"
docker info | grep -i runtime
