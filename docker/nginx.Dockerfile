FROM nginx:stable-alpine3.24

# The official image uses OpenSSL during package verification, but EOS also
# needs the openssl CLI at runtime to create the short-lived first-boot
# certificate before Let's Encrypt succeeds.
RUN apk add --no-cache openssl ca-certificates \
    && rm -rf /var/cache/apk/*
