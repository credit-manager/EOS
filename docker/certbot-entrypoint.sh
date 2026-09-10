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
        return 0
    fi
    return 1
}

request_certificate() {
    # Only the configured canonical hostname is requested. An optional www
    # alias must be explicitly configured in DNS and can be added later without
    # making the first production boot depend on it.
    certbot certonly \
        --webroot -w "$WEBROOT" \
        --cert-name "$CERT_NAME" \
        --keep-until-expiring \
        --non-interactive \
        --agree-tos \
        --email "$ACME_EMAIL" \
        --no-eff-email \
        -d "$DOMAIN"
}

while ! sync_certificates; do
    if ! request_certificate; then
        echo "WARNING: Let's Encrypt issuance failed; retrying in 15 minutes" >&2
        sleep 15m
    fi
done

echo "EOS: trusted TLS certificate is active."

while :; do
    sleep 12h
    certbot renew --non-interactive || echo "WARNING: certbot renewal attempt failed" >&2
    sync_certificates || true
done
