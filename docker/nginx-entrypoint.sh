#!/bin/sh
set -eu

: "${DOMAIN:?DOMAIN is required}"

envsubst '${DOMAIN}' < /etc/nginx/eos.conf.template > /etc/nginx/conf.d/eos.conf

exec nginx -g 'daemon off;'
