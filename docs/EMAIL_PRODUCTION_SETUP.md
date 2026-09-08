# EOS Production Email & Organization Invitations

EOS supports a real SMTP provider for production email. Development/test can continue using the console provider.

## Production configuration

Set these environment variables in the deployment platform's secret/environment configuration (never commit real credentials):

```text
EOS_AUTH_MODE=production
EOS_EMAIL_PROVIDER=smtp
EOS_SMTP_HOST=smtp.example.com
EOS_SMTP_PORT=587
EOS_SMTP_USERNAME=<smtp-username>
EOS_SMTP_PASSWORD=<smtp-password-or-app-password>
EOS_FROM_EMAIL=noreply@your-domain.example
EOS_FROM_NAME=EOS Platform
EOS_FRONTEND_URL=https://app.your-domain.example
```

For Gmail/Google Workspace, use an authenticated SMTP account and an app password where required. For a transactional email provider, use the SMTP credentials supplied by that provider.

## Password reset

`POST /api/v1/auth/forgot-password` creates a short-lived reset token and sends the reset URL through the configured provider. The token itself is not returned when the provider is SMTP.

`POST /api/v1/auth/reset-password` consumes the token and revokes existing refresh sessions after the password is changed.

The response remains intentionally generic when the email address does not exist to prevent account enumeration.

## Organization invitations

An authenticated organization administrator can call:

`POST /api/v1/invitations`

with:

```json
{
  "email": "new.user@example.com",
  "first_name": "New",
  "last_name": "User",
  "role": "user"
}
```

The invitation is tenant-scoped. EOS does not email a temporary password. It creates an inactive credential state with a single-use, hashed invitation token and sends an acceptance link valid for 72 hours.

The recipient accepts it with:

`POST /api/v1/invitations/accept`

```json
{
  "token": "<invitation-token>",
  "password": "A-new-password1"
}
```

After acceptance, the user is marked email-verified, the invitation token is invalidated, and the user can sign in normally.

## Operational rule

Do not put SMTP passwords, API keys, app passwords, or other credentials in Git. Configure them through the production secret manager/environment. The repository only documents the variable names and expected behavior.
