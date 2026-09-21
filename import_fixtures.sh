#!/bin/bash
# ==============================================================================
# Helper Script: Load Fixtures into PostgreSQL
# ==============================================================================
set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BACKEND_DIR"

echo "==> Loading Departments, Brands, and Models into PostgreSQL..."
docker compose -f ../Hardware-Inventory-System-/docker-compose.yml exec -T backend python manage.py loaddata fixtures/brands_departments_models.json

echo "==> Done!"
