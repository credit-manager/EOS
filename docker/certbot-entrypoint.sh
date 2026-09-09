#!/bin/sh
set -eu

: "${DOMAIN:?DOMAIN is required}"
: "${ACME_EMAIL:?ACME_EMAIL is required for Let's Encrypt issuance}"

CERT_NAME="$DOMAIN"
LE_DIR="/etc/letsencrypt/live/$CERT_NAME"
TLS_DIR="/etc/eos-tls"
WEBROOT="/var/www/certbot"

mkdir -p "$TLS_DIR" "$WEBROOT/.well-known/acme-challenge"

sync_certificates() {
    if [ -s "$LE_DIR/fullchain.pem" ] && [ -s "$LE_DIR/privkey.pem" ]; then
        cp "$LE_DIR/fullchain.pem" "$TLS_DIR/fullchain.pem.tmp"
        cp "$LE_DIR/privkey.pem" "$TLS_DIR/privkey.pem.tmp"
        chmod 0644 "$TLS_DIR/fullchain.pem.tmp"
        chmod 0600 "$TLS_DIR/privkey.pem.tmp"
        mv "$TLS_DIR/fullchain.pem.tmp" "$TLS_DIR/fullchain.pem"
        mv "$TLS_DIR/privkey.pem.tmp" "$TLS_DIR/privkey.pem"
    fi
}

request_certificate() {
    certbot certonly \
        --webroot -w "$WEBROOT" \
        --cert-name "$CERT_NAME" \
        --keep-until-expiring \
        --non-interactive \
        --agree-tos \
        --email "$ACME_EMAIL" \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
}

if ! request_certificate; then
    echo "WARNING: initial Let's Encrypt issuance failed; continuing with bootstrap TLS" >&2
fi
sync_certificates

while :; do
    sleep 12h
    certbot renew --non-interactive || echo "WARNING: certbot renewal attempt failed" >&2
    sync_certificates
done
