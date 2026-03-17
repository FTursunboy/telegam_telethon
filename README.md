# TelegramApiServerManagement Python Rewrite

Новый проект на Python (без Laravel) с совместимыми API/Webhook контрактами.

## Stack
- FastAPI + uvicorn
- Telethon
- MySQL + SQLAlchemy + Alembic
- Docker Compose

## Run
```bash
docker compose up --build
```

После старта API будет доступен на `http://localhost:18000`.
Параметры запуска меняются в файле `.env`.

## API
Маршруты совместимы:
- `POST /api/v1/login/start`
- `POST /api/v1/login/complete-code`
- `POST /api/v1/login/complete-2fa`
- `POST /api/v1/session/stop`
- `POST /api/v1/session/restart`
- `POST /api/v1/session/status`
- `POST /api/v1/send-message`
- `POST /api/v1/send-voice`
- `POST /api/v1/send-file`
- `POST /api/v1/react-message`
- `POST /api/v1/edit-message`
- `POST /api/hs/data/coordinates`
