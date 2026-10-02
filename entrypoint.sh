#!/usr/bin/env bash
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Checking and seeding master fixtures..."
python manage.py loaddata fixtures/brands_departments_models.json

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting backend server..."
exec "$@"
