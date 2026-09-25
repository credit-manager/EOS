# 2TO EOS - Deployment Guide

## Quick Start (Development)

```bash
# Backend
cd backend
pip install -e ".[test]"
uvicorn backend.app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Production Deployment

### Prerequisites
- Docker & Docker Compose
- Domain name with SSL
- Minimum 2GB RAM

### Steps

1. Clone the repository
```bash
git clone https://github.com/credit-manager/EOS.git
cd EOS
```

2. Create `.env` file
```bash
cp .env.example .env
# Edit .env with your production values
```

3. Start services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. Run database migrations
```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

5. Create the initial admin user

The first registration creates the first workspace and its admin. Use an environment-provided password — never a static one from documentation.

```bash
export ADMIN_EMAIL='admin@yourdomain.com'
export ADMIN_PASSWORD="$(openssl rand -base64 24)"
echo "Admin password for $ADMIN_EMAIL: $ADMIN_PASSWORD"
curl -sS -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\",\"tenant_name\":\"Your Organization\"}"
```

Rotate this password after first login and store it in a secrets manager.

### SSL Setup (Let's Encrypt)

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Auto-renew
certbot renew --dry-run
```

### Backup

```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U 2toeos 2toeos > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T db psql -U 2toeos 2toeos < backup.sql
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register user |
| POST | /api/v1/auth/token | Login |
| GET | /api/v1/health | Health check |
| GET | /api/v1/reports/dashboard | Dashboard stats |
| GET | /api/v1/reports/financial/summary | Financial summary |
| GET | /api/v1/reports/financial/profit-loss | Profit & Loss |
| GET | /api/v1/export/construction/projects | Export projects |
| GET | /api/v1/notifications | List notifications |
| GET | /api/v1/permissions/roles | List roles |

## License

Proprietary - 2TO EOS
