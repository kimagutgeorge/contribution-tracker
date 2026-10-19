# Contribution Tracker

A public page that lists contributions, plus a **Sign in** button so an admin can add, edit and delete entries on that same page.

- **frontend/**: Vue 3 + Vite. In production it is built and served by nginx, which also proxies `/api` to the backend.
- **backend/**: Flask + SQLAlchemy + gunicorn.
- **db**: Postgres 16 (data kept in the `pgdata` volume).

## How the fields work

| Field | Meaning |
|---|---|
| name, date | Who contributed and when (for a pledge, the date it was made) |
| pledged | Toggle. Off = a one-off payment. On = a pledge paid in installments |
| amount | Pledge on: the pledged total. Pledge off: the amount paid |
| paid | Pledge on: the sum of all its payments. Pledge off: same as amount |
| balance | Pledge on: what is still owed (never below zero). Pledge off: none |

Every installment towards a pledge is stored in a `payments` table (date + amount). Click a pledge's name, or its "N payments" link, to open its history: each payment with the balance left after it. When signed in, the admin can record, edit and delete payments there.

If payments go past the pledge (pledge 1000, pay 300 + 200 + 800), the pledge shows as cleared and the extra 300 is listed as paid over the pledge.

Upgrading from the first version is automatic: on start, any amount already paid on a pledge becomes that pledge's first payment, and the old `paid` column is removed.

## Deploy on Coolify

1. Push this repo to GitHub, GitLab or another Git host.
2. In Coolify: **New Resource → Docker Compose**, pick the repo, and leave the compose file as `docker-compose.yml`.
3. Under **Environment Variables**, set:
   - `POSTGRES_PASSWORD`: a strong password
   - `SECRET_KEY`: a long random string (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `ADMIN_USERNAME`: optional, defaults to `admin`
   - `ADMIN_PASSWORD`: the admin login password
4. Assign your domain to the **frontend** service, using port 1404 (for example `https://contributions.example.com:1404`; Coolify serves it on normal HTTPS and only uses 1404 to reach the container). Do not expose `backend` or `db`.
5. Deploy. Tables are created automatically on first start.

To change the admin password, update `ADMIN_PASSWORD` and redeploy. Changing `SECRET_KEY` signs out everyone.

## Run locally with Docker

```bash
cp .env.example .env   # then edit the values
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

Open http://localhost:1404.

## Develop without Docker

You need a Postgres database somewhere. Then:

```bash
# API on http://localhost:5003
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/contributions
export SECRET_KEY=dev ADMIN_PASSWORD=admin123
.venv/bin/python init_db.py
.venv/bin/flask --app wsgi run --debug --port 5003

# Frontend on http://localhost:1404 (proxies /api to :5003)
cd frontend
npm install && npm run dev
```

Tests: `cd backend && .venv/bin/python -m pytest`

## Customising

- Site title and currency: `frontend/src/config.js`
- Colours: CSS variables at the top of `frontend/src/style.css`

## API

| Method | Path | Auth |
|---|---|---|
| GET | `/api/contributions` | public (items + totals) |
| POST | `/api/auth/login` | returns a bearer token (valid 12 hours) |
| GET | `/api/auth/me` | bearer |
| POST | `/api/contributions` | bearer |
| PUT | `/api/contributions/<id>` | bearer |
| DELETE | `/api/contributions/<id>` | bearer |
| POST | `/api/contributions/<id>/payments` | bearer (pledges only) |
| PUT | `/api/payments/<id>` | bearer |
| DELETE | `/api/payments/<id>` | bearer |
| GET | `/api/health` | public |
