#!/bin/sh
set -eu

: "${DOMAIN:?DOMAIN is required}"
TLS_DIR=/etc/eos-tls
FULLCHAIN="$TLS_DIR/fullchain.pem"
PRIVKEY="$TLS_DIR/privkey.pem"

mkdir -p "$TLS_DIR"

if [ ! -s "$FULLCHAIN" ] || [ ! -s "$PRIVKEY" ]; then
  echo "EOS: generating temporary self-signed certificate for first boot..."
  umask 077
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  openssl req -x509 -nodes -newkey rsa:2048 -days 7 \
    -subj "/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN},DNS:www.${DOMAIN}" \
    -keyout "$tmpdir/privkey.pem" \
    -out "$tmpdir/fullchain.pem" >/dev/null 2>&1
  chmod 0600 "$tmpdir/privkey.pem"
  chmod 0644 "$tmpdir/fullchain.pem"
  mv "$tmpdir/privkey.pem" "$PRIVKEY"
  mv "$tmpdir/fullchain.pem" "$FULLCHAIN"
  rm -rf "$tmpdir"
  trap - EXIT
fi

envsubst '${DOMAIN}' < /etc/nginx/eos.conf.template > /etc/nginx/conf.d/eos.conf
nginx -t

# Certbot atomically replaces the shared certificate files. Reload Nginx when
# the certificate fingerprint changes so renewal takes effect without downtime.
last_fingerprint=""
(
  while :; do
    sleep 30
    if [ -s "$FULLCHAIN" ] && [ -s "$PRIVKEY" ]; then
      fingerprint="$(sha256sum "$FULLCHAIN" | awk '{print $1}')"
      if [ -n "$last_fingerprint" ] && [ "$fingerprint" != "$last_fingerprint" ]; then
        nginx -t && nginx -s reload || echo "WARNING: Nginx certificate reload failed" >&2
      fi
      last_fingerprint="$fingerprint"
    fi
  done
) &

exec nginx -g 'daemon off;'
