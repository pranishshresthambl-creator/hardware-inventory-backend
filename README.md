# Hardware Inventory Backend

Django REST Framework backend for Hardware Inventory System.

## 🚀 Quick Start with Docker (PostgreSQL)

If you are using Docker, run:

```bash
# 1. Create .env from template
cp .env.example .env

# 2. Build and start containers
docker compose up -d --build

# 3. Apply database migrations
docker compose exec backend python manage.py migrate

# 4. Create admin / supervisor account
docker compose exec backend python manage.py createsuperuser

# 5. (Optional) Seed vendor data
docker compose exec backend python manage.py seed_vendors
```

The API will be live at `http://localhost:8000/`.

---

## 💻 Local Setup without Docker (SQLite)

```bash
# 1. Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create admin user
python manage.py createsuperuser

# 5. Run development server
python manage.py runserver
```
