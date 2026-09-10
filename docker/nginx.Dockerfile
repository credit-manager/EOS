FROM nginx:stable-alpine3.24

# Refresh the Alpine package index and installed packages so the image does
# not retain vulnerable OS libraries from the base image snapshot. The
# openssl CLI is required by the EOS first-boot TLS bootstrap entrypoint.
RUN apk upgrade --no-cache \
    && apk add --no-cache openssl ca-certificates \
    && rm -rf /var/cache/apk/*
