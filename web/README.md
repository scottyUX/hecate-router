# Hecate Lab webpage

Static single-page site for the Hecate research project. No build step required.

## Preview locally

From the repository root:

```bash
python -m http.server 8080 --directory web
```

Open http://localhost:8080

## Deploy

### GitHub Pages

1. In the repo settings, enable **Pages** → source: **GitHub Actions**.
2. Push to `main`; the workflow in `.github/workflows/deploy-web.yml` publishes `web/`.

Site URL (after first deploy): `https://scottyUX.github.io/hecate/` (if the repo is public) or your org's Pages URL.

### Any static host

Upload the contents of `web/` to Netlify, Vercel, Cloudflare Pages, etc. Set the publish directory to `web`.

## Editing

- `index.html` — page structure and copy
- `styles.css` — theme and layout
- `main.js` — pipeline scroll highlight (optional)

Update the **Status** section in `index.html` as milestones complete.
