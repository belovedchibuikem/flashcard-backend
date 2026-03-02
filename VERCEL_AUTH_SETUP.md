# Vercel Auth Setup - Fix "Could not validate credentials"

## Required: Set JWT_SECRET_KEY in Vercel

The `/auth/me` and other protected routes return 401 "Could not validate credentials" when `JWT_SECRET_KEY` is not set or differs between serverless instances.

### Steps

1. **Generate a secret** (run locally):
   ```bash
   openssl rand -hex 32
   ```

2. **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**
3. Add:
   - **Name:** `JWT_SECRET_KEY` (exactly this; the backend also checks `JWT_SECRET`)
   - **Value:** Paste the output from step 1
   - **Environments:** Production, Preview, Development

4. **Redeploy** the project after adding the variable (Deployments → ⋮ → Redeploy).

### Why this matters

- Login creates a JWT signed with `JWT_SECRET_KEY`
- `/auth/me` validates the token using the same secret
- On Vercel serverless, login and `/auth/me` can hit different instances
- All instances must use the **same** `JWT_SECRET_KEY` from env vars

### Debug endpoint (when DEBUG=true)

`GET /api/auth/verify-token` with `Authorization: Bearer <token>` returns:
- `{"valid": true, "payload": {...}}` if JWT decodes successfully
- `{"valid": false, "error": "..."}` if JWT decode fails

This helps identify whether the 401 is from JWT validation or user lookup.
