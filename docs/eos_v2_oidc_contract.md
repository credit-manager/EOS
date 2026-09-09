# EOS v2 OIDC Authentication Contract

## Production policy

Production authentication uses an external OIDC identity provider. EOS validates access tokens locally against the provider's JWKS and never accepts unsigned tokens.

Required production settings:

- `EOS_AUTH_MODE=oidc`
- `EOS_OIDC_ISSUER`
- `EOS_OIDC_AUDIENCE`
- `EOS_OIDC_JWKS_URL`

`EOS_OIDC_ISSUER` and `EOS_OIDC_JWKS_URL` must use HTTPS in production.

## Token requirements

EOS accepts only RS256 access tokens on the OIDC path. The JWT must contain:

- `iss` matching the configured issuer
- `aud` matching the configured API audience
- `exp`
- `sub`
- `tenant_id`
- `actor_id`

After cryptographic validation, EOS resolves the tenant and actor from its own identity database and verifies that the actor belongs to the claimed tenant and is active. Database membership therefore remains authoritative for authorization.

## JWKS caching and rotation

The application uses PyJWT's JWKS client with a five-minute JWKS cache. The external identity provider remains responsible for signing-key rotation and overlap. EOS does not generate or expose ephemeral signing keys.

## Development compatibility

`EOS_AUTH_MODE=hs256` remains available for isolated development/test deployments so local tests do not require an external identity provider. It is not accepted by the production security gate.

## Multi-tenant identity model

The identity provider authenticates the human/service subject; EOS authorizes access to a tenant through its persisted actor/tenant relationship. For users belonging to multiple tenants, the identity layer must issue an EOS-compatible token containing the selected tenant and actor claims, or a trusted gateway must perform that mapping before the EOS API is called.
