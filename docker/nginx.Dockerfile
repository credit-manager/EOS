FROM nginx:stable-alpine3.24

# Keep the image patched at build time. Alpine v3.24 currently ships
# libuuid 2.42.3-r1, which contains the fixes for the util-linux issues
# detected by the infrastructure security gate.
RUN apk update \
    && apk upgrade --no-cache \
    && apk add --no-cache 'libuuid=2.42.3-r1' openssl ca-certificates \
    && rm -rf /var/cache/apk/*
