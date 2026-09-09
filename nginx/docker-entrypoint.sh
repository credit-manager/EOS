#!/bin/bash
# EOS Nginx Entry Point — Environment Variable Substitution
# Replaces ${DOMAIN} in eos.conf with actual domain value

set -e

# Use default if DOMAIN not set
DOMAIN=${DOMAIN:-localhost}

# Substitute environment variables in nginx config
envsubst '${DOMAIN}' < /etc/nginx/conf.d/eos.conf.template > /etc/nginx/conf.d/eos.conf

# Start nginx
exec nginx -g "daemon off;"
