# Feature Specification: OpenRouter Client Wrapper

**Feature Branch**: `007-openrouter-client`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "OpenRouter client wrapper: HTTP client with timeout, retry/backoff, bounded concurrency, and per-call token usage capture for Stage-1 patch generation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get one attempted fix for a task (Priority: P1)

A Stage-1 operator (or the generation runner) has a rendered prompt for one task and a chosen model. They send the prompt to that model and receive back the model's generated text plus the token counts the call consumed, so the outcome can be recorded for that (task, model) pair.

**Why this priority**: This is the core deliverable of S7 — without a call that returns text plus usage, no patch can be generated, extracted (S8), or costed. Every later Stage-1 step depends on it.

**Independent Test**: Provide one prompt string and one valid model slug; confirm the call returns non-empty generated text along with prompt-token and completion-token counts, using the run's fixed decoding parameters.

**Acceptance Scenarios**:

1. **Given** a valid prompt and a configured model slug, **When** a single generation is requested, **Then** the result contains the generated text, the prompt-token count, the completion-token count, and the decoding parameters that were used.
2. **Given** the run's configured decoding parameters, **When** the same prompt and slug are sent again, **Then** the request uses the identical decoding parameters and those parameters are reported back on the result.

---

### User Story 2 - Survive transient provider failures (Priority: P1)

Across a large sweep (hundreds of calls per model), the provider will intermittently rate-limit or return temporary server errors. The operator needs individual calls to recover from these transient failures automatically instead of losing samples.

**Why this priority**: A 1,200-call sweep cannot complete reliably if every transient rate-limit or 5xx aborts a sample. Automatic recovery is essential to collect the full counterfactual matrix.

**Independent Test**: Simulate a sequence of transient failures (rate-limit / temporary server error / timeout) followed by success, and confirm the call ultimately returns a successful result; simulate a permanent client error (e.g. bad request / unauthorized) and confirm it fails immediately without wasted retries.

**Acceptance Scenarios**:

1. **Given** a call that fails transiently (rate-limit, server error, timeout, or connection drop) and then would succeed, **When** the call is made, **Then** it retries with increasing back-off and returns the eventual successful result.
2. **Given** a call that keeps failing transiently, **When** the retry budget is exhausted, **Then** the call surfaces a clear error indicating the failure and the attempts made.
3. **Given** a call that fails with a permanent client error (malformed request, unauthorized, forbidden), **When** the call is made, **Then** it fails fast without retrying.

---

### User Story 3 - Keep concurrency and spend bounded (Priority: P2)

The operator wants to run many generations together for throughput, but must not exceed a safe number of simultaneous in-flight requests to the provider.

**Why this priority**: Bounded concurrency protects against provider throttling and runaway parallel spend while still allowing the sweep to finish in reasonable time. It builds on the single-call behavior (P1) rather than being required to demonstrate one call.

**Independent Test**: Issue more concurrent generation requests than the configured limit and confirm that the number of simultaneously in-flight calls never exceeds that limit.

**Acceptance Scenarios**:

1. **Given** a configured maximum concurrency of N, **When** more than N generations are requested at once, **Then** no more than N calls are in flight at any moment and all requests eventually complete.

---

### Edge Cases

- Provider returns a success response but omits token-usage fields — the result must still be usable and signal that usage is unavailable rather than crashing.
- A request exceeds the configured timeout — treated as a transient failure eligible for retry.
- The API key is missing — the operator gets a clear, actionable error before any network call is attempted.
- An unknown or unconfigured model slug is requested — surfaced as a clear error.
- Retry back-off must not retry indefinitely; there is a bounded, configurable cap on attempts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST send a single rendered prompt to a specified model and return the model's generated text.
- **FR-002**: System MUST return the prompt-token count and completion-token count when the provider reports usage for a call, suitable for recording on a per-(task, model) generation record; when usage is not reported, these counts MUST be explicitly absent (`None`) rather than fabricated.
- **FR-003**: System MUST use decoding parameters sourced from the run configuration (temperature, max tokens) and MUST report the exact parameters used back on the result.
- **FR-004**: System MUST apply a request timeout to every call.
- **FR-005**: System MUST automatically retry transient failures (rate-limiting, temporary server errors, timeouts, and connection errors) using increasing back-off, up to a bounded, configurable number of attempts.
- **FR-006**: System MUST NOT retry deterministic client errors (e.g. malformed request, unauthorized, forbidden) and MUST fail fast on them.
- **FR-007**: System MUST surface a clear error when the retry budget is exhausted, distinguishable from a permanent-failure error.
- **FR-008**: System MUST cap the number of simultaneously in-flight calls at a configurable maximum.
- **FR-009**: System MUST load the provider credential from the environment and MUST fail with an actionable message if it is absent; the credential MUST NOT be hard-coded or logged.
- **FR-010**: System MUST send exactly the provided prompt to the model and MUST NOT append any solution, gold-patch, or answer content.
- **FR-011**: System MUST target the provider base endpoint defined in the run configuration and accept any of the run's configured model slugs.
- **FR-012**: System MUST be verifiable without live network access, so the behavior above can be exercised deterministically in tests without incurring provider spend.

### Key Entities *(include if feature involves data)*

- **Generation request**: The inputs to one model call — the prompt string, the target model slug, and the decoding parameters for the run.
- **Completion result**: The outputs of one model call — generated text, prompt-token count, completion-token count, the model slug, and the decoding parameters used. Maps onto the existing per-(task, model) generation record fields.
- **Run configuration**: The provider base endpoint, decoding parameters, and set of allowed model slugs that make calls reproducible across a run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single generation for a valid prompt and slug returns non-empty text in 100% of successful calls; prompt-token and completion-token counts are returned whenever the provider reports usage, and are explicitly `None` (never fabricated) when the provider omits usage.
- **SC-002**: When a call encounters transient failures before eventually succeeding, it recovers and returns a successful result without operator intervention.
- **SC-003**: Permanent client errors fail on the first attempt with no retries, and exhausted-retry failures are reported distinctly from permanent failures.
- **SC-004**: With a concurrency limit of N, the number of simultaneously in-flight calls never exceeds N across a batch larger than N.
- **SC-005**: The full behavior set is exercised by automated tests that run offline with zero provider spend, so the suite passes in CI without a live credential.
- **SC-006**: Given the same prompt, slug, and configured decoding parameters, the parameters recorded on the result are identical run to run.

## Assumptions

- The rendered prompt is produced upstream (S6); this feature consumes it as an opaque string and does not construct or modify prompt content.
- The run configuration (provider base endpoint, decoding parameters, and verified model slugs) already exists and is authoritative for this feature.
- The provider credential is supplied via the environment loader established in S2; provisioning the credential itself is out of scope.
- Cost accounting and budget enforcement, patch extraction/normalization, response caching, and the JSONL generation runner are handled by separate features and are out of scope here; this feature only returns text and usage.
- Single-shot generation (one prompt in, one response out) is assumed; multi-turn or tool-loop interactions are out of scope for v1.
