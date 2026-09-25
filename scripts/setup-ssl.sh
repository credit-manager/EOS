#!/bin/bash
# SSL Certificate Setup using Let's Encrypt + Certbot
# Run this on the production server after DNS is configured

set -e

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}

echo "============================================"
echo "  SSL Certificate Setup for $DOMAIN"
echo "============================================"

# Install certbot (Ubuntu/Debian)
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Get certificate
echo "Requesting SSL certificate..."
certbot certonly --nginx \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL"

# Auto-renewal cron
echo "Setting up auto-renewal..."
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -

# Reload nginx
echo "Reloading nginx..."
nginx -t && systemctl reload nginx

echo ""
echo "SSL certificate installed successfully!"
echo "Certificate expires in 90 days (auto-renewal configured)"
