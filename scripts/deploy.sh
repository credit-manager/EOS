#!/bin/bash
# EOS Production Deployment Script
# Usage: ./scripts/deploy.sh [domain] [email]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOMAIN=${1:-${DOMAIN}}
EMAIL=${2:-${LETSENCRYPT_EMAIL}}

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: DOMAIN not provided${NC}"
    echo "Usage: ./scripts/deploy.sh your-domain.com admin@your-domain.com"
    exit 1
fi

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Email for Let's Encrypt not provided${NC}"
    echo "Usage: ./scripts/deploy.sh your-domain.com admin@your-domain.com"
    exit 1
fi

# Load environment
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       EOS Dynamic Business Platform — Deployment             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# ═══════════════════════════════════════════════
# 1. Validate production config
# ═══════════════════════════════════════════════
echo -e "${YELLOW}▶ Validating production configuration...${NC}"
python core/production_config.py || {
    echo -e "${RED}Production config validation failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Configuration valid${NC}"
echo ""

# ═══════════════════════════════════════════════
# 2. Build and start containers
# ═══════════════════════════════════════════════
echo -e "${YELLOW}▶ Building Docker images...${NC}"
docker-compose build --no-cache api

echo -e "${YELLOW}▶ Starting database...${NC}"
docker-compose up -d db

echo -e "${YELLOW}▶ Waiting for database to be healthy...${NC}"
timeout=60
while ! docker-compose exec -T db pg_isready -U $POSTGRES_USER -d $POSTGRES_DB >/dev/null 2>&1; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo -e "${RED}Database startup timeout${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ Database ready${NC}"

echo -e "${YELLOW}▶ Starting API...${NC}"
docker-compose up -d api

echo -e "${YELLOW}▶ Waiting for API to be healthy...${NC}"
timeout=60
while ! curl -sf http://localhost:8000/health >/dev/null 2>&1; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo -e "${RED}API startup timeout${NC}"
        docker-compose logs api
        exit 1
    fi
done
echo -e "${GREEN}✓ API ready${NC}"

# ═══════════════════════════════════════════════
# 3. Obtain SSL certificate
# ═══════════════════════════════════════════════
echo -e "${YELLOW}▶ Obtaining Let's Encrypt certificate for $DOMAIN...${NC}"

# Start nginx with HTTP-only config first
docker-compose up -d nginx

# Wait for nginx
sleep 5

# Get certificate
docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot -w /var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN || {
    echo -e "${RED}Certificate generation failed${NC}"
    echo "Make sure DNS is pointing to this server"
    exit 1
}

echo -e "${GREEN}✓ Certificate obtained${NC}"

# ═══════════════════════════════════════════════
# 4. Reload nginx with SSL config
# ═══════════════════════════════════════════════
echo -e "${YELLOW}▶ Reloading nginx with SSL...${NC}"
docker-compose exec nginx nginx -s reload

echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}EOS is now running at: https://$DOMAIN${NC}"
echo -e "${GREEN}API docs: https://$DOMAIN/docs${NC}"
echo -e "${GREEN}Landing:  https://$DOMAIN/app${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"