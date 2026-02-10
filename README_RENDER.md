# Deploy on Render

This project is now configured for Render deployment.

## Option 1: Blueprint (recommended)
1. Push your repository to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select your repository.
4. Render will read `render.yaml` and create:
   - Web service `lab-stock`
   - PostgreSQL database `lab-stock-db`

## Option 2: Manual Web Service
Use these settings:
- Build Command: `./build.sh`
- Start Command: `./start.sh`
- Environment: `Python`

Set environment variables:
- `SECRET_KEY` (required)
- `DEBUG=false`
- `ALLOWED_HOSTS=.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://*.onrender.com`
- `DATABASE_URL` (from Render PostgreSQL service)

## Notes
- Static files are collected during build.
- Migrations run during build.
- App runs with Gunicorn.
