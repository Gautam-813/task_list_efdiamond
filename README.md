# Shared Task Management App

Local-first FastAPI task management web app with admin-created users, shared tasks, filters, and a grey Bootstrap UI.

## Run locally

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

Default local admin:

- Username: `admin`
- Password: `admin123`

Change these before deployment.

