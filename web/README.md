# Hecate Lab webpage

Next.js app for the Hecate research lab site (auth, journal, and public homepage).

## Preview locally

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000

## Deploy

Production is hosted on Railway (`hecate-production`). Push to the connected branch to redeploy.

Production URL: `https://hecate-production.up.railway.app`

### Supabase Auth URLs (password reset / invites)

In the **hecate** Supabase project → **Authentication → URL configuration**:

| Setting | Value |
|---------|--------|
| **Site URL** | `https://hecate-production.up.railway.app` (**not** `http://localhost:3000`) |
| **Redirect URLs** | `https://hecate-production.up.railway.app/auth/callback` |
| | `https://hecate-production.up.railway.app/auth/confirm` |
| | `https://hecate-production.up.railway.app/auth/set-password` |
| | `http://localhost:3000/auth/callback` |
| | `http://localhost:3000/auth/confirm` |
| | `http://localhost:3000/auth/set-password` |

Also set Railway (and local if needed):

```bash
NEXT_PUBLIC_SITE_URL=https://hecate-production.up.railway.app
```

If a reset email already redirected to `localhost` with `otp_expired`, that link is dead — fix Site URL, then request a **new** reset from the production site (or local, after allowlist includes localhost), and open it in the **same browser** that requested it (PKCE).
