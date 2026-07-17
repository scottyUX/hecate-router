# Quickstart: Stage-1 Prompt Template

## Prerequisites

- Repo installed editable (`pip install -e ".[dev]"` or project equivalent)
- S5 context builder available (`hecate.scaffold.build_context`)

## Validation scenarios

### 1. Synthetic render (offline)

```bash
pytest tests/test_scaffold.py -k "prompt" -q
```

Expect: issue text and file contents present; determinism; gold patch absent; `PROMPT_VERSION == "v1"`.

### 2. Real Lite instance (network + cache)

```bash
pytest tests/test_scaffold.py -k "real_lite_instance_prompt" -q
```

Expect: `build_context` + `render_prompt` for a known Lite id (e.g. `psf__requests-1963`) yields a non-empty prompt containing the problem statement and context file path(s), without the gold patch.

### 3. Manual smoke (optional)

```python
from hecate.data.tasks import get_task
from hecate.scaffold import build_context, render_prompt, prompt_hash, PROMPT_VERSION

task = get_task("psf__requests-1963")
bundle = build_context(task.instance_id, method="oracle", task=task)
prompt = render_prompt(task, bundle)
assert PROMPT_VERSION == "v1"
assert task.patch not in prompt
print(prompt_hash(prompt), len(prompt))
```

## Expected outcomes

| Check | Pass criteria |
|-------|----------------|
| Render | Non-empty string with Issue + files + Instructions |
| Shared scaffold | Same task/context → identical string |
| No leakage | `task.patch` not in prompt |
| Version | `PROMPT_VERSION` recorded / stable |
