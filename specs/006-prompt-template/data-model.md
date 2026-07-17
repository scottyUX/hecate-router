# Data Model: Stage-1 Prompt Template

## Entities (consumed)

### SwebenchTask (existing — S3)

| Field | Role in S6 |
|-------|------------|
| `instance_id` | Optional metadata in prompt |
| `repo` | Shown in prompt header |
| `problem_statement` | Issue body |
| `patch` | **Must not** appear in prompt |
| `base_commit` | Not required in prompt body (files already at base); available on task |

### ContextBundle / ContextFile (existing — S5)

| Field | Role in S6 |
|-------|------------|
| `files` | Ordered `(path, content)` pairs embedded in prompt |
| `instance_id`, `repo`, `base_commit`, `method` | Available; prefer task fields for issue text; method not needed in prompt |

## Entities (produced)

### Rendered prompt

- Type: `str`
- Properties: deterministic for `(task, context, version)`; includes instructions for one unified diff
- Invariants: no gold patch text; identical across models

### Prompt version

- Constant: `PROMPT_VERSION` (e.g. `"v1"`)
- Recorded with runs / available to callers

### Prompt hash

- `prompt_hash(prompt: str) -> str` — SHA-256 hex of UTF-8 bytes
- Maps to `GenerationRecord.prompt_hash`

### Prompt ref (optional)

- Path string returned by `write_prompt`
- Maps to `GenerationRecord.prompt_ref`

## Validation rules

1. Unsupported `version` → error (do not silently fall back to another template).
2. Empty `context.files` → still valid render (issue + instructions only).
3. Never read or append `task.patch` into the prompt body.
