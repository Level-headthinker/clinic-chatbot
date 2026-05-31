#!/bin/bash
# Run this on your VPS to deploy latest code
# Usage: ./deploy.sh

set -e

echo "Pulling latest code..."
git pull origin main

echo "Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

echo "Rebuilding and restarting containers..."
docker-compose up -d --build

echo "Done. App is running."
