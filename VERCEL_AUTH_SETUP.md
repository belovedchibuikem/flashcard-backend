# Vercel Auth Setup - Fix "Could not validate credentials"

## How Token Verification Works (Tokens Are NOT Stored in Database)

This app uses **stateless JWT** authentication:

1. **Login** (`POST /auth/login`): Server signs a JWT with `JWT_SECRET_KEY` and returns it. The token contains `{sub: user_id, exp: expiry}`.
2. **Protected routes** (e.g. `GET /auth/me`): Client sends `Authorization: Bearer <token>`. Server verifies the token by:
   - Decoding it with `JWT_SECRET_KEY` (cryptographic signature check)
   - If valid, extracting `user_id` from the payload
   - Looking up the user in the database
3. **Tokens are never stored** in the database. The client holds the token; the server only verifies it using the secret.

**Critical:** The same `JWT_SECRET_KEY` must be used for both signing (login) and verifying (/auth/me). If they differ, `jwt.decode()` fails.

---

## Required: Set JWT_SECRET_KEY in Vercel

### Steps

1. **Generate a secret** (run locally):
   ```bash
   openssl rand -hex 32
   ```

2. **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**
3. Add:
   - **Name:** `JWT_SECRET_KEY`
   - **Value:** Paste the output from step 1
   - **Environments:** Production, Preview, Development

4. **Redeploy** the project (Deployments → ⋮ → Redeploy).

5. **Log in again** – Old tokens were signed with the previous secret. After changing `JWT_SECRET_KEY`, you must log in again to get a fresh token.

---

## Diagnostic Endpoints

### `GET /api/auth/diagnose` (no auth required)

Returns whether `JWT_SECRET_KEY` is configured:
```json
{
  "secret_configured": true,
  "secret_length": 64,
  "is_default_secret": false,
  "is_vercel": true,
  "hint": "..."
}
```

If `secret_configured` is false, the env var is not set or is still the default.

### `GET /api/auth/verify-token` (requires Bearer token)

Tests JWT decode only (no DB lookup):
- `{"valid": true, "payload": {...}}` – token decodes OK
- `{"valid": false, "error": "..."}` – token was signed with a different secret (or expired)

---

## Common Causes of Persistent 401

| Cause | Fix |
|-------|-----|
| Token from before redeploy | **Log in again** to get a token signed with the new secret |
| Token from localhost / different deployment | Log in on the Vercel deployment |
| `JWT_SECRET_KEY` only set for Preview, not Production | Add for all environments |
| Trailing space in env var | Re-enter the value in Vercel, no spaces |
