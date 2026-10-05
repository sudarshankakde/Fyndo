# 11 - Deployment & Infrastructure Specification

> **Platform**: Docker Multi-Container Compose (Local & Staging) | AWS ECS / VPS (Production)

---

## 1. Docker Compose Services Topology

```yaml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:16-3.4-alpine
    container_name: fyndo-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: fyndo_db
      POSTGRES_USER: fyndo_user
      POSTGRES_PASSWORD: fyndo_secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: fyndo-redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: fyndo-api
    command: uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql+asyncpg://fyndo_user:fyndo_secure_password@postgres:5432/fyndo_db
      REDIS_URL: redis://redis:6379
      JWT_ACCESS_SECRET: your_super_secret_jwt_key
    depends_on:
      - postgres
      - redis

  # media-worker: (DEFERRED FOR BETA - To be enabled when adaptive HLS streaming is required)
  #   build:
  #     context: ./backend
  #     dockerfile: Dockerfile.worker
  #   container_name: fyndo-worker
  #   command: celery -A app.workers.celery_app worker --loglevel=info
  #   environment:
  #     DATABASE_URL: postgresql+asyncpg://fyndo_user:fyndo_secure_password@postgres:5432/fyndo_db
  #     REDIS_URL: redis://redis:6379
  #   depends_on:
  #     - postgres
  #     - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: fyndo-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  pgdata:
  redisdata:
```

---

## 2. Environment Configuration Matrix

| Variable | Description | Required Environment |
|---|---|---|
| `ENVIRONMENT` | `development` \| `production` | All |
| `PORT` | API Server Port (Default `5000`) | All |
| `DATABASE_URL` | PostgreSQL async connection string (`postgresql+asyncpg://...`) | All |
| `REDIS_URL` | Redis connection for sessions, OTP TTL, and rate limiting | All |
| `JWT_ACCESS_SECRET` | Cryptographic secret for access tokens | All |
| `JWT_REFRESH_SECRET`| Secret for refresh tokens | All |
| `CLOUDINARY_CLOUD_NAME`| Cloudinary account cloud name | All |
| `CLOUDINARY_API_KEY` | Cloudinary API Key for signing uploads | All |
| `CLOUDINARY_API_SECRET`| Cloudinary API Secret for backend signature generation | All |
| `CLOUDINARY_URL` | Cloudinary complete connection string | All |
| `SMS_GATEWAY_API_KEY`| Twilio / Gupshup API Key for OTP dispatch | Staging / Prod |

---

## 3. Production Deployment Architecture
- **Reverse Proxy**: Nginx with automated Let's Encrypt SSL/TLS certificates.
- **Media Delivery & Edge CDN**: Cloudinary multi-CDN fabric handles automatic media routing, dynamic WebP format delivery, and responsive video delivery.
- **Process Management**: Docker containers with auto-restart policies and health check endpoints (`/api/v1/health`).
