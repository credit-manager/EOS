# EOS DBP — Production Deployment Guide
## From Dev to First Real Customer

---

## Current State

```
Development Environment:
├── OS: Windows (dev machine)
├── Python 3.14
├── PostgreSQL 18
├── Server: 127.0.0.1:8000
├── Tests: 599/599 PASS
└── Status: Production Certified ✅
```

---

## Phase 1: VPS Selection & Setup

### Recommended VPS Options

| Provider | Min Specs | Monthly Cost | Best For |
|----------|-----------|--------------|----------|
| **Hetzner** | 4 vCPU, 8GB RAM | ~$20 | Best value |
| **DigitalOcean** | 4 vCPU, 8GB RAM | ~$40 | Easy setup |
| **Linode** | 4 vCPU, 8GB RAM | ~$40 | Reliable |
| **Vultr** | 4 vCPU, 8GB RAM | ~$40 | Global |
| **AWS Lightsail** | 4 vCPU, 8GB | ~$40 | AWS ecosystem |

### Recommended Minimum Specs

```
Production VPS:
├── CPU: 4 cores
├── RAM: 8 GB
├── Storage: 80 GB SSD
├── OS: Ubuntu 22.04 LTS
├── Bandwidth: 4 TB
└── Cost: $20-50/month
```

---

## Phase 2: VPS Initial Setup

```bash
# 1. SSH into VPS
ssh root@your-vps-ip

# 2. Update system
apt update && apt upgrade -y

# 3. Create deploy user
adduser eos
usermod -aG sudo eos
su - eos

# 4. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker eos

# 5. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## Phase 3: Domain & SSL

### Option A: With Domain (Recommended)

```bash
# 1. Point DNS to VPS
# A Record: app.yourdomain.com → VPS IP
# A Record: api.yourdomain.com → VPS IP

# 2. Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# 3. Get SSL Certificate
sudo certbot certonly --standalone -d app.yourdomain.com -d api.yourdomain.com

# 4. Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option B: Without Domain (Testing)

```bash
# Use IP directly with self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/eos-selfsigned.key \
  -out /etc/ssl/certs/eos-selfsigned.crt
```

---

## Phase 4: Production Database Setup

```bash
# 1. PostgreSQL setup
sudo -u postgres psql

# Inside PostgreSQL:
CREATE USER eos WITH PASSWORD 'YOUR_SECURE_PASSWORD';
CREATE DATABASE eos_main OWNER eos;
GRANT ALL PRIVILEGES ON DATABASE eos_main TO eos;
\q

# 2. Enable remote access (if needed)
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: host eos_main eos 0.0.0.0/0 md5

sudo systemctl restart postgresql
```

---

## Phase 5: Deploy EOS DBP

### Option A: Manual Deploy

```bash
# 1. Clone/copy project
cd /home/eos
git clone https://github.com/yourusername/eos-dbp.git
# OR upload zip via scp

# 2. Create .env.production
cp .env.production.example .env.production
nano .env.production
```

**.env.production:**
```env
DATABASE_URL=postgresql://eos:YOUR_SECURE_PASSWORD@localhost:5432/eos_main
SECRET_KEY=GENERATE_A_RANDOM_64_CHAR_STRING
ENCRYPTION_KEY=GENERATE_ANOTHER_RANDOM_64_CHAR_STRING
CORS_ORIGINS=https://app.yourdomain.com
ALLOWED_HOSTS=api.yourdomain.com,localhost
```

```bash
# 3. Install dependencies
cd eos-dbp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Import database
PGPASSWORD=YOUR_SECURE_PASSWORD pg_dump -h localhost -U eos -d eos_main > /tmp/eos_backup.sql
# Copy from dev machine and restore:
PGPASSWORD=YOUR_SECURE_PASSWORD psql -h localhost -U eos -d eos_main < /tmp/eos_backup.sql

# 5. Run server
python main.py
```

### Option B: Docker Deploy (Recommended)

```bash
# 1. Create docker-compose.prod.yml
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:14-alpine
    restart: always
    environment:
      POSTGRES_USER: eos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: eos_main
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"

  api:
    build: .
    restart: always
    env_file: .env.production
    depends_on:
      - db
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./backups:/app/backups

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - api

volumes:
  postgres_data:
EOF

# 2. Deploy
docker-compose -f docker-compose.prod.yml up -d
```

---

## Phase 6: Nginx Configuration

**nginx/nginx.prod.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Upstream
    upstream eos_api {
        server api:8000;
    }

    # HTTP → HTTPS redirect
    server {
        listen 80;
        server_name app.yourdomain.com api.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # API
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://eos_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Frontend (when ready)
    server {
        listen 443 ssl http2;
        server_name app.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;

        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

---

## Phase 7: Backup & Monitoring

### Automated Backup

```bash
# Create backup script
cat > /home/eos/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/eos/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PGPASSWORD=$DB_PASSWORD pg_dump -h localhost -U eos eos_main | gzip > $BACKUP_DIR/eos_$DATE.sql.gz
# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

chmod +x /home/eos/backup.sh

# Add to crontab
crontab -e
# Daily backup at 3 AM
0 3 * * * /home/eos/backup.sh
```

### Monitoring

```bash
# Simple health check cron
cat > /home/eos/health_check.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$RESPONSE" != "200" ]; then
    echo "EOS DBP is down! Response: $RESPONSE" | mail -s "EOS Alert" admin@yourdomain.com
    # Restart
    cd /home/eos/eos-dbp && docker-compose restart api
fi
EOF

chmod +x /home/eos/health_check.sh
crontab -e
# Check every 5 minutes
*/5 * * * * /home/eos/health_check.sh
```

---

## Phase 8: Create First Tenant

### 1. Access Admin

```
https://api.yourdomain.com/api/v1/auth/login
Email: admin@demo.com
Password: admin123
```

### 2. Create Real Company

```bash
# Via API
curl -X POST https://api.yourdomain.com/api/v1/dynamic/saas/tenants \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "First Customer Company",
    "company_name_ar": "أول شركة عميل",
    "slug": "first-customer",
    "industry": "trading",
    "contact_email": "info@firstcustomer.com",
    "contact_phone": "+966501234567"
  }'
```

### 3. Setup Company Data

```bash
# Create default data for the company
curl -X POST https://api.yourdomain.com/api/v1/dynamic/companies/default/trading/items \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_code": "PROD001",
    "item_name": "First Product",
    "category": "General",
    "unit_price": 100
  }'
```

---

## Deployment Checklist

```
PRE-DEPLOYMENT
├── [ ] VPS purchased and accessible
├── [ ] Domain pointed to VPS
├── [ ] SSL certificate obtained
├── [ ] PostgreSQL installed and configured
├── [ ] Environment variables set
└── [ ] Firewall configured (UFW)

DEPLOYMENT
├── [ ] EOS code deployed to VPS
├── [ ] Database restored from backup
├── [ ] Server starts without errors
├── [ ] API responds to /health
├── [ ] HTTPS working
└── [ ] Nginx configured

POST-DEPLOYMENT
├── [ ] Admin login works
├── [ ] First tenant created
├── [ ] Company data initialized
├── [ ] Backup cron active
├── [ ] Monitoring cron active
└── [ ] Test real workflow
```

---

## First Customer Onboarding Flow

```
1. CREATE TENANT
   └── Company name, industry, admin user

2. SETUP COMPANY
   └── Chart of accounts, warehouses, price lists

3. ADD STARTING DATA
   └── Items, customers, suppliers (opening balances)

4. TRAIN USER
   └── Login, create item, create invoice, view reports

5. GO LIVE
   └── Real transactions, real invoices, real reports

6. GATHER FEEDBACK
   └── What works, what needs improvement

7. ITERATE
   └── EOS 1.x updates based on real usage
```

---

## Summary

```
EOS DBP Production Deployment:
├── VPS: Hetzner/DigitalOcean ($20-50/mo)
├── Domain: app.yourdomain.com + api.yourdomain.com
├── SSL: Let's Encrypt (free)
├── Database: PostgreSQL 14
├── Server: Docker + Nginx
├── Backup: Daily automated
├── Monitoring: Health checks
└── First Customer: Trading/Restaurant/etc.

Total Monthly Cost: ~$25-60
Setup Time: 2-4 hours
Time to First Customer: Same day
```
