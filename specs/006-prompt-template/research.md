# Research: Stage-1 Prompt Template

## Decision: Module layout

**Decision**: Implement in `src/hecate/scaffold/prompt.py`; re-export from `hecate.scaffold`.

**Rationale**: S5 already owns `context.py`. Keeping prompt rendering separate avoids bloating context and matches the pipeline split (S5 → S6).

**Alternatives considered**: Put everything in `__init__.py` (harder to maintain); redefine local `ContextBundle` (rejected — S5 landed).

## Decision: Consume S5 `ContextBundle` as-is

**Decision**: `render_prompt(task: SwebenchTask, context: ContextBundle, *, version: str | None = None) -> str` takes the real S5 bundle. File order follows `context.files` (already deterministic from oracle patch order).

**Rationale**: Shared scaffold requires same paths/contents as S5; re-sorting by path would diverge from `GenerationRecord.context_files` order.

**Alternatives considered**: Sort paths alphabetically (prior draft on `s6/prompt-template`); rejected for order fidelity to S5.

## Decision: Frozen version string `PROMPT_VERSION = "v1"`

**Decision**: Explicit module-level `PROMPT_VERSION = "v1"`. `render_prompt` defaults to it; unsupported versions raise `ValueError`.

**Rationale**: Issue requires freeze/version for reproducibility and S9 cache keys. A short version string is clearer in records than hashing the template source alone; `prompt_hash` still covers full rendered content.

**Alternatives considered**: Content-hash of template source only; version + hash together (hash still available via helper).

## Decision: Hash algorithm

**Decision**: SHA-256 hex digest of UTF-8 prompt bytes via `hashlib`.

**Rationale**: Stable, stdlib, suitable for cache keys and `GenerationRecord.prompt_hash`.

**Alternatives considered**: blake2b (fine, less ubiquitous in docs); MD5 (weaker, unnecessary).

## Decision: Optional persistence

**Decision**: `write_prompt(prompt: str, *, output_dir: Path | str | None = None) -> str` writes `{prompt_hash}.txt` under `data/cache/prompts/` by default and returns that path string as `prompt_ref`.

**Rationale**: Aligns with existing gitignored `data/cache/` and generation-record `prompt_ref` field. Optional so unit tests need not touch disk.

**Alternatives considered**: Always persist (heavier); store under `data/outputs/` only (also fine; cache is closer to S5 clone cache).

## Decision: Template wording

**Decision**: Freeze illustrative structure from issue #6: repo line, Issue section, Relevant files at base_commit, Instructions demanding one unified diff and no extra explanation. Include `instance_id` as a single metadata line under the header for traceability without solution leakage.

**Rationale**: Matches S8 expected output format; minimal metadata per FR-009.

**Alternatives considered**: Multi-turn agent prompts (out of scope); per-model variants (forbidden by shared scaffold).
