# Sikhiya Backend

FastAPI backend for the Sikhiya learning platform.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration

3. **Run Locally**
   ```bash
   uvicorn app.main:app --reload
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Database connection string |
| `SECRET_KEY` | Yes | JWT secret key |
| `ADMIN_EMAIL` | Yes | Admin account email |
| `ADMIN_PASSWORD` | Yes | Admin account password |
| `ADMIN_NAME` | Yes | Admin display name |
| `CORS_ORIGINS` | Yes | Allowed frontend origins (comma-separated) |
| `MIGRATE_DB` | No | Set to 'true' to run migrations (MySQL only) |
| `MAIL_USERNAME` | No | Email account for password reset |
| `MAIL_PASSWORD` | No | Email account password |
| `MAIL_FROM` | No | Email sender address |
| `MAIL_PORT` | No | SMTP port (default: 587) |
| `MAIL_SERVER` | No | SMTP server (default: smtp.gmail.com) |
| `MAIL_FROM_NAME` | No | Email sender name |

## Deployment to Railway

1. Create a new project on [Railway](https://railway.app)
2. Add MySQL plugin to your project
3. Set environment variables in Railway dashboard
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Deploy from GitHub or using Railway CLI

## Project Structure

```
sikhiya-backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── database.py       # Database configuration
│   ├── models.py         # SQLAlchemy models
│   └── admin_config.py   # Admin configuration
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md            # This file
```

## API Endpoints

- `POST /register` - User registration
- `POST /login` - User authentication
- `GET /courses` - List courses
- `POST /courses` - Create course (teacher/admin)
- `GET /admin/*` - Admin endpoints
- And more...

## Development

The backend uses SQLite by default for local development. For production, use MySQL with Railway.
