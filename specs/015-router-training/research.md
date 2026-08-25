# Research: Router Training v1

## D1 — Optional `train` extra, not default deps

**Decision**: `torch` and `transformers` live under `[project.optional-dependencies] train`. Default `pip install -e ".[dev]"` stays offline-friendly.

**Rationale**: Constitution III — CI must not download 100MB+ weights. ModernBERT is only needed for the live experiment.

**Alternatives considered**: Pin torch in default deps (rejected — CI cost/size); call Hugging Face from a notebook only (rejected — no manifest).

## D2 — Scripted encoder backend

**Decision**: `EncoderBackend` protocol with `ScriptedBackend` (deterministic scores from instance id) and `ModernBertBackend` (imported only when selected).

**Rationale**: Tests cover splits + Route-AUC without torch. Live path is one CLI flag.

**Alternatives considered**: Tiny random `nn.Embedding` in CI (still needs torch installed).

## D3 — Route-AUC definition

**Decision**: For λ from 0 to 1, policy uses m1 if p ≥ λ else m2. Routed resolve rate is the fraction of tasks where the chosen model’s `resolved` is true. Route-AUC = ∫₀¹ (rate(λ) − always_m2) dλ, trapezoid over a dense λ grid (including 0 and 1).

**Rationale**: Issue #18 go/no-go is Route-AUC > 0, so the metric must be able to be ≤ 0. sklearn ROC-AUC is 0.5 at chance and cannot express “no lift vs always-m2”.

**Alternatives considered**: ROC-AUC of m1 label (kept as a secondary diagnostic, not the go/no-go bit).

## D4 — Tokenization in tests vs live

**Decision**: Dataset truncation uses a `Tokenizer` protocol. Tests use whitespace splitting. Live ModernBERT uses the model tokenizer. Budget is 2048 tokens either way.

**Rationale**: Truncation rate must be testable offline.

## D5 — Stratification fallback

**Decision**: Try (label, repo) strata. If any stratum has fewer examples than n_folds, try repo-only, then unstratified round-robin. Record `split_strategy` on the manifest.

**Rationale**: The 20-task slice had 0 m1 positives; full 300 may still be too sparse for 5-way label×repo strata.

## D6 — Input text source

**Decision**: Use the m1 generation record `prompt` (shared scaffold: issue + oracle files). Do not concatenate `extracted_patch`.

**Rationale**: Issue #18: issue + oracle file; patch is not input. Re-fetching files from SWE-bench is unnecessary when the prompt already contains them.
