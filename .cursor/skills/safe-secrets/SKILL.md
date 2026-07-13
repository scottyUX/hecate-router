---
name: safe-secrets
description: Audit changes for leaked secrets and keep credentials out of git. Use when adding auth, API keys, .env files, credentials, tokens, or when the user mentions secrets or environment variables.
---

# Safe secrets

## Rules

- Real secrets live only in local `.env` (or a secret manager) — never in source, tests fixtures with production keys, docs, or commits.
- Commit `.env.example` with empty or placeholder values and short comments.
- Ensure `.gitignore` includes `.env` (and common variants like `.env.local` if used).
- Never print secrets in logs, CLI help, exception messages, or CI output.

## Workflow

1. **Scan the diff** for high-risk patterns: `API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PRIVATE_KEY`, `Bearer `, `sk-`, PEM blocks.
2. **Check ignore rules**: `.env` must be ignored; confirm with `git check-ignore -v .env` when unsure.
3. **Check staged/untracked files** before commit: no `.env`, credential JSON, or key material.
4. If a secret was already committed, **stop** and warn the user — rotating the secret is required; removing it from history alone is not enough.
5. Prefer a small env helper that:
   - loads dotenv for local dev
   - reads `os.environ`
   - raises a clear error when a required key is missing

## Checklist

```
- [ ] No real secrets in tracked files
- [ ] .env gitignored
- [ ] .env.example has placeholders only
- [ ] Diff reviewed for accidental key material
```
