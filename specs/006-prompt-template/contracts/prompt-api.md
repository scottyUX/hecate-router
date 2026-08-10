# Contract: Prompt template API

Public surface of `hecate.scaffold` for S6 (additive to S5 exports).

## Constants

```python
PROMPT_VERSION: str  # frozen template id, e.g. "v1"
```

## Functions

### `render_prompt`

```python
def render_prompt(
    task: SwebenchTask,
    context: ContextBundle,
    *,
    version: str | None = None,
) -> str:
    """Deterministic prompt for one task. Same inputs → same string for every model."""
```

- Default `version` is `PROMPT_VERSION`.
- Raises `ValueError` if `version` is not supported.
- Must not include `task.patch`.
- Must instruct a single unified-diff response.

### `prompt_hash`

```python
def prompt_hash(prompt: str) -> str:
    """SHA-256 hex digest of UTF-8 prompt bytes."""
```

### `write_prompt` (optional helper)

```python
def write_prompt(
    prompt: str,
    *,
    output_dir: Path | str | None = None,
) -> str:
    """Write prompt to disk; return path string suitable for prompt_ref."""
```

- Default directory: repo `data/cache/prompts/`.
- Filename based on `prompt_hash(prompt)` for content-addressable storage.

## Invariants

1. Shared scaffold: `model_slug` is not an input.
2. Single-shot: no tool/agent loop in the prompt contract.
3. Determinism: identical `(task fields used, context.files, version)` → identical bytes.
