# Self-hosted fonts

Loaded by `app/layout.tsx` with `next/font/local`, so builds never fetch from
Google Fonts (Railway's builder could not reach it on 12 Nov 2026).

Latin subset, from Fontsource on npm:

| File | Package | Weights |
|------|---------|---------|
| `figtree-latin-wght-normal.woff2` | `@fontsource-variable/figtree@5.3.0` | 300–900 (variable) |
| `fraunces-latin-wght-normal.woff2` | `@fontsource-variable/fraunces@5.3.0` | 100–900 (variable) |
| `source-serif-4-latin-wght-normal.woff2` | `@fontsource-variable/source-serif-4@5.3.1` | 200–900 (variable) |
| `ibm-plex-mono-latin-400-normal.woff2` | `@fontsource/ibm-plex-mono@5.3.0` | 400 |
| `ibm-plex-mono-latin-500-normal.woff2` | `@fontsource/ibm-plex-mono@5.3.0` | 500 |

All are under the SIL Open Font License 1.1.
