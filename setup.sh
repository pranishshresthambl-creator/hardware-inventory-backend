#!/bin/bash
set -e

echo "🚀 Starting 1-Step Setup..."

# Remove any conflicting containers
docker rm -f postgres_db hardware_inventory_backend 2>/dev/null || true
docker compose down -v --remove-orphans 2>/dev/null || true

# Start Docker containers
docker compose up -d --build

echo "⏳ Waiting for database..."
sleep 3

# Migrate and load initial data
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py loaddata initial_data.json

echo "✅ ALL DONE! Backend is live at http://localhost:8000/ with all 98 computers and data!"
