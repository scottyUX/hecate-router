---
name: verify-install
description: Verify a clean Python package install and smoke tests after dependency or env changes. Use when changing pyproject.toml, requirements, .env loading, setup instructions, or when the user asks whether install works.
---

# Verify install

## When to use

After dependency edits, env-loading changes, or packaging updates — before calling the work done.

## Workflow

1. Confirm the install entrypoint (`pyproject.toml`, `requirements.txt`, etc.) lists the packages you expect.
2. Create a **fresh** virtualenv (do not reuse a dirty local env for the proof):

```bash
python3 -m venv /tmp/project-install-check
/tmp/project-install-check/bin/pip install -U pip
/tmp/project-install-check/bin/pip install -e ".[dev]"
```

Adjust the install command to match the repo (e.g. `pip install -r requirements.txt`).

3. Run a minimal verification:
   - Import core dependencies
   - Run targeted pytest if present (`pytest -q` or a subset)
4. If the change involves env loading, confirm:
   - `.env` is gitignored
   - `.env.example` documents required keys without real secrets
   - Code loads keys from the environment / dotenv as designed
5. Report pass/fail with the exact commands run and any errors.

## Checklist

```
- [ ] Fresh venv install succeeds
- [ ] Core imports work
- [ ] Targeted tests pass (if any)
- [ ] Secrets not required for unit smoke (or clearly documented)
```

## Notes

- Prefer proving install in an isolated venv over “it works on my machine.”
- Clean up temporary venvs when done if disk use matters.
