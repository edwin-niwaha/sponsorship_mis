# Sponsorship Management System (SMS)

A secure, production-ready Django web application for managing child sponsorships and processing donations via **MTN Mobile Money (MoMo) in Uganda.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Django](https://img.shields.io/badge/django-4.2%2B-success)
![PostgreSQL](https://img.shields.io/badge/db-postgresql-blue)
![Coverage](coverage.svg)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Full MTN MoMo Collections API integration (Uganda)
- Real-time payment status polling (no keys exposed to browser)
- Secure webhook/callback handling with idempotency
- Donor capture (name, email, phone)
- Admin dashboard with search & pagination
- 90%+ test coverage with detailed reports
- Clean, responsive UI with Bootstrap

## Live Demo (when deployed)
→ https://your-live-url.com (add later)

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/edwin-niwaha/sponsorship-mis.git
cd sponsorship-mis/backend
```
### 2. Set up virtual environment
```bash
python -m venv .smsvenv

# Windows Terminal
.venv\Scripts\activate

```bash
source .smsvenv/Scripts/activate

# macOS / Linux
source venv/bin/activate
```bash
### 3. Install dependencies
```bash
pip install -r requirements.txt
python -m pip install --upgrade pip setuptools wheel

pip freeze > requirements.txt
```bash
### 4. Set up environment variables
```bash
cp .env.example .env
```
### 5. Apply migrations & create admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```
### 6. Run the server
Set this in `.env` for local development:
```bash
DJANGO_ENV=development
```

Then run:
```bash
python manage.py runserver
```
Open → http://localhost:8000

Production uses `core.settings.production`. Set `DJANGO_ENV=production` in the
hosting environment.

For Google OAuth in development, add this authorized redirect URI in Google
Cloud Console:
```text
http://localhost:8000/oauth/complete/google-oauth2/
```

### Testing & Coverage 
```bash
# Install coverage (one time)
pip install coverage coverage-badge

# Run tests with coverage
coverage run manage.py test

# View report in terminal
coverage report -m

# Generate HTML report (recommended)
coverage html
# Open htmlcov/index.html in your browser

# Generate coverage badge
coverage-badge -o coverage.svg
```
### Code Quality
```bash
# Lint with flake8
pip install flake8
flake8
```
