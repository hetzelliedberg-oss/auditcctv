#!/bin/bash
# 1-Click Deployment Script for Ubuntu / Debian / Cloud VPS (AWS, GCP, DigitalOcean, Hetzner)
echo "=== Deploying Xiaomi CCTV AI Store Analytics to Cloud ==="
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker

# Build and start in background
docker compose down || true
docker compose build
docker compose up -d

echo "========================================================"
echo "🎉 System is running 24/7 in the cloud!"
echo "Access Dashboard at: http://$(curl -s ifconfig.me):8501"
echo "========================================================"
