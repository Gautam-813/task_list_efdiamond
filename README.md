# Shared Task Management App

FastAPI task management web app with admin-created users, shared tasks, comments, attachments, priorities, filters, activity logging, and user management.

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

**Default admin credentials (change immediately in production):**

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

---

## Production deployment (Ubuntu)

### 1. System dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql nginx certbot
```

### 2. Create the app user and directory

```bash
sudo useradd -r -s /bin/false -d /opt/task_app -m www-data 2>/dev/null || true
sudo mkdir -p /opt/task_app
sudo chown www-data:www-data /opt/task_app
```

### 3. Deploy the code

```bash
# as root or via deploy pipeline
git clone https://github.com/your-org/task_app.git /opt/task_app
cd /opt/task_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example /opt/task_app/.env
# Edit /opt/task_app/.env with your production values:
#   ENVIRONMENT=production
#   DATABASE_URL=postgresql://user:password@localhost:5432/task_app
#   SECRET_KEY=<random hex>
#   DEFAULT_ADMIN_PASSWORD=<strong password>
nano /opt/task_app/.env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Set up PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER task_app WITH PASSWORD 'your-strong-password';"
sudo -u postgres psql -c "CREATE DATABASE task_app OWNER task_app;"
```

### 6. Run database migrations

```bash
cd /opt/task_app
source venv/bin/activate
alembic upgrade head
```

### 7. Set up systemd service

```bash
sudo cp deploy/task_app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now task_app
sudo systemctl status task_app
```

### 8. Set up Nginx reverse proxy

```bash
sudo cp deploy/task_app.nginx.conf /etc/nginx/sites-available/task_app
sudo ln -s /etc/nginx/sites-available/task_app /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Obtain SSL certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

### 9. Set up backups

Add a daily cron job:

```bash
sudo crontab -e
```

Add the line:

```
0 3 * * * /opt/task_app/deploy/backup.sh /opt/task_app/backups
```

---

## Database migrations (Alembic)

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Templates | Jinja2 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5.3 + custom CSS |
| Migrations | Alembic |

