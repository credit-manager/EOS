#!/bin/bash
# SSL Certificate setup with Let's Encrypt
DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}

echo "Setting up SSL for $DOMAIN"

# Initial nginx config without SSL
cp nginx.conf nginx.prod.conf

# Start services
docker compose -f docker-compose.prod.yml up -d frontend

# Get certificate
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email "$EMAIL" --agree-tos --no-eff-email \
  -d "$DOMAIN" -d "www.$DOMAIN"

# Switch to SSL config
docker compose -f docker-compose.prod.yml restart frontend

echo "SSL setup complete for $DOMAIN"
