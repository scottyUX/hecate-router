# Task: Reuse E7 telemetry and define the routing State Builder

- **Task ID:** TASK-004
- **Status:** Approved for implementation on a separate branch.
- **Created:** 2026-11-19
- **Scope:** Turn existing execution logs into a reproducible routing observation, independent of the final M1/M2 choice.
- **Authorization:** Scott requested this task specification in the same style as the earlier tasks. Scott approved implementation on a separate branch on 2026-11-19 ("on a seperate branch we can build this task"). Scope remains offline telemetry/state construction.

## Description

Reuse the logging foundation from Experiment 7 and the TASK-001/002/003 harnesses
instead of introducing another independent logging system. Define a versioned
execution-event contract and implement, after review, a deterministic Telemetry
Collector and State Builder for mid-task routing.

The State Builder consumes only information available at the routing checkpoint.
It produces a fixed numeric observation plus validity masks for a future router.
Final evaluator outcomes stay on the evaluation/reward path. This task does not
train PPO, choose M1/M2, execute escalation or establish advisor score quality.

## Specifications

### Architecture and code organization

```text
Harness events + model usage + optional advisor assessment
    → versioned event adapters
    → Telemetry Collector
    → State Builder
    → observation vector + validity mask + schema version

Final patch → independent SWE evaluator → outcome/reward records
```

Proposed modules, subject to the reuse assessment:

```text
src/hecate/telemetry/
  events.py             # canonical event and identity contract
  adapters.py           # E7, Codex and mini-SWE-agent log adapters
  collector.py          # causal counters, windows and usage ledger
src/hecate/router/
  state.py              # observation schema, masks and normalization
configs/
  routing_observation.yaml
scripts/
  replay_routing_observations.py
```

Do not import a mutable sibling checkout at runtime. Record the exact source
commit and files for any E7 code reused or adapted. Preserve historical records;
conversion writes a new artifact rather than modifying original logs.

### Existing recording to assess for reuse

Inspect these files in `/Users/scottdavis/advisor-models`:

- `advisor_models/swe_smith/agent_server.py`: optional session JSONL logging
  (`--log-dir`), initialization, actions/observations, advice, cumulative steps,
  termination and student cost.
- `advisor_models/swe_smith/eval_swe_smith.py`: per-task identity, final patch,
  evaluator identity/outcome, steps, cost, status and errors.
- `advisor_models/swe_smith/codex_proxy.py`: timestamped request/response events,
  usage, advice delivery/compaction tracking, request/tool counters and limits.
- `advisor_models/swe_smith/eval_codex.py`: Codex events, proxy logs, per-task rows,
  run metadata and advisor guidance history.
- Current Hecate `src/hecate/execution/` modules: raw model/tool records,
  termination reasons, immutable manifests, artifact checksums and mirroring.

This is an implementation inventory, not a claim that every E7 run retained
all optional logs. Inventory actual available training/pilot artifacts before
choosing replay fixtures. Missing historical fields remain missing.

### Event contract

Pin a schema version. Each canonical event contains:

- Run, episode, task and session identity; harness name/version and source log
  reference. Identify the coding-model role and pinned model revision when known.
- Stable event identity and episode ordering; timestamp and clock source when
  supplied. Preserve request, attempt/retry and tool-call correlation IDs.
- Event type: model request/response/failure, tool start/completion/failure,
  advisor assessment, checkpoint or episode termination.
- Typed payload: command/result references, exit status, usage, elapsed time,
  active model and termination reason as applicable.
- Provenance and explicit availability/quality flags for inferred or missing
  fields. Preserve original step labels rather than redefining them.

Keep model requests, transport attempts, completed tool interactions and advisor
calls as separate counters. E7 Codex's request-based `steps` must not be relabeled
as completed tool interactions. Never count streamed fragments or duplicate
completion notifications as additional actions.

### Routing checkpoints

Proposed initial cadence: every five completed tool interactions, before the
next model request, with no stream or tool call in flight. A completed failed
command still counts as an interaction; an incomplete command does not. An
episode ending before the next checkpoint produces a terminal record, not an
invented routing decision. Include an initial observation before the first
model request if the reviewed routing protocol allows an initial decision.

This task defines and replays logical checkpoints. Live pause/resume and model
handoff belong to the session-controller task. Historical logs lacking enough
ordering or correlation evidence must be marked checkpoint-unverifiable rather
than asserted equivalent to live checkpoints.

### Proposed observation schema v1

Freeze names, order, units, windows and masks in configuration before integration.
Use these candidate groups for review:

1. **Budget and progress counters:** completed interactions, model requests,
   request-budget fraction used, elapsed episode time and time-budget fraction
   used. Unknown configured limits produce missing fractions.
2. **Recent execution:** command failure fraction over the latest five completed
   commands; timeout count; repeated exact normalized error signatures in that
   window. Version the deterministic signature rule. These measure observed
   behavior, not semantic correctness or proof of being stuck.
3. **Visible tests:** pass/fail counts and change since the last comparable visible
   test run, only when explicit test identities, parser version and execution
   conditions establish comparability. Arbitrary stdout is not test evidence.
4. **Usage and context:** cumulative reported input/output tokens, inference
   duration and latest measured input-context utilization when available. Declare
   whether cached tokens are a subset of input tokens; never add them twice.
   Requests with missing usage make full cumulative totals incomplete.
5. **Routing context:** active model role and action-availability mask supplied by
   the controller. Keep action masks distinct from missing-feature masks.
6. **Optional advisor assessment:** progress, stuckness, remaining difficulty and
   confidence scores, each with validity and freshness information. Reserve the
   slots; without a separately validated assessment producer they remain missing.
   E7's advice text is not automatically a calibrated numeric assessment.

The raw numeric vector, feature mask and action mask are separate named outputs.
The router input may concatenate numeric values and feature masks according to
the pinned schema. Keep free-text commands, advice and rationales in audit logs,
not in the initial numeric observation.

### Calculations and missingness

```text
request_budget_used = model_requests / configured_request_limit
command_failure_rate = failed_completed_commands / completed_commands_in_window
context_used = latest_reported_input_tokens / configured_context_limit

z_i = (x_i - mean_i) / max(std_i, epsilon)
```

A missing numerator, zero/unknown denominator or incompatible measurement yields
`valid_i = 0`, not a meaningful zero. For standardized continuous features,
impute missing values with the training mean (therefore normalized value zero)
and append the validity mask. Pin handling for categorical/counter fields and
out-of-range values; do not silently clip values without a configured rule.

Fit normalization on designated training observations only; retain fitting IDs,
counts and hashes. Freeze the normalizer before validation/evaluation. A feature
with no valid training observations stays disabled/masked; zero variance uses the
pinned epsilon. An initial raw replay can run without fitted normalization, but
must label itself raw and must not claim to produce deployment-ready observations.

Retain measured duration and token units separately. Cost weights, token-price
proxies, reference cost and PPO rewards are separate experimental decisions;
local API charges of zero do not imply zero compute cost. Advisor overhead stays
separately identifiable, including when historical logs did not record it.

### Concrete schemas — v1

These are the readable data contracts for the JSON/JSONL records. `number` means
finite JSON number; unavailable measurements use `null`. Fields marked `?` are
optional because historical producers do not supply them. Schema/config hashes
are SHA-256 strings. The feature order is fixed by
`configs/routing_observation.yaml`; it is not derived from JSON object ordering.

#### 1. Canonical execution event

One JSONL line represents one event. Identity stays constant within an episode;
`sequence` increases within that episode. `event_id` identifies duplicates.

```typescript
type Identity = {
  run_id: string;
  task_id: string;
  session_id: string;
  harness: string;
  harness_version: string;
  split: "train" | "pilot";
  model_revision: string | null;
};

type ExecutionEvent = {
  version: "hecate.events.v1";
  episode_id: string;
  event_id: string;
  sequence: number;                  // nonnegative integer; episode-local order
  kind: "controller" | "model_request" | "model_response" | "model_failure"
      | "tool_start" | "tool_complete" | "advisor_call" | "advisor_assessment"
      | "visible_tests" | "boundary" | "termination" | "legacy_step";
  source: string;                    // source log reference
  timestamp: number | null;          // seconds in the explicitly named clock
  clock: string | null;              // e.g. "unix" or "monotonic"
  identity: Identity;
  quality: string[];                 // e.g. ["checkpoint_unverifiable"]
  payload: EventPayload;             // selected by kind, described below
};
```

Payload contracts:

```typescript
type ControllerPayload = {
  active_model?: "m1" | "m2";
  action_mask?: [boolean, boolean];  // [stay, escalate]; at least one true
  request_limit?: number | null;
  wall_limit_s?: number | null;
  context_limit?: number | null;
  episode_start?: boolean;           // true only with an observed start timestamp
};

type RequestPayload = { request_id: string };

type ResponsePayload = {
  request_id: string;
  attempts: number | null;           // transport attempts, including retries
  input_tokens: number | null;       // includes cached input when provider does
  output_tokens: number | null;
  inference_s: number | null;        // measured, not estimated from token count
};                                  // also used for model_failure

type ToolStartPayload = { tool_id: string };

type ToolCompletePayload = {
  tool_id: string;
  command: boolean;                 // whether this interaction is a shell command
  exit_code?: number | null;
  timeout?: boolean | null;
  error_text?: string | null;        // explicit error evidence, not a guessed cause
  start_verified?: boolean;          // absent means a correlated start is required
};

type AdvisorCallPayload = {
  request_id?: string;
  legacy_step?: number;
};

type AdvisorAssessmentPayload = {
  schema: "hecate.assessment.v1";
  validated: boolean;
  progress?: number | null;          // valid scores lie in [0, 1]
  stuckness?: number | null;
  remaining_difficulty?: number | null;
  confidence?: number | null;
};

type VisibleTestsPayload = {
  selection_id: string;              // exact test selection identity
  conditions_id: string;             // comparable execution conditions
  parser_version: string;
  tests: Record<string, "passed" | "failed">; // explicit test IDs
};

type BoundaryPayload = { verified: boolean };
type TerminationPayload = { reason: string };

// Diagnostic legacy_step payloads preserve source labels such as legacy_step,
// legacy_total_steps and legacy_cost. They do not establish tool checkpoints.
// EventPayload is the corresponding payload above, selected by event.kind.
```

A `boundary` declares the point before another model request. The collector still
checks that no model response or tool completion is pending, enough interactions
have completed, and ordering is verifiable. A termination event creates no routing
decision. Advisor freshness is measured from the assessment's position in the
event sequence and the number of subsequent completed interactions.

#### 2. Routing observation / State Builder output

```typescript
type Features = {
  completed_interactions: number | null; // count
  model_requests: number | null;         // agent decisions, not transport attempts
  transport_attempts: number | null;     // includes retries
  advisor_calls: number | null;         // separate from coding-model requests
  request_budget_used: number | null;    // requests / request limit
  elapsed_s: number | null;              // requires a known episode start/clock
  time_budget_used: number | null;       // elapsed seconds / episode wall limit
  command_failure_rate: number | null;   // recent completed commands; [0, 1]
  command_timeouts: number | null;       // count in the configured command window
  repeated_errors: number | null;        // duplicate exact normalized signatures
  visible_passed: number | null;         // most recent structured visible test run
  visible_failed: number | null;
  visible_pass_delta: number | null;     // only between comparable test records
  input_tokens: number | null;           // cumulative, full coverage required
  output_tokens: number | null;
  inference_s: number | null;            // cumulative, full coverage required
  context_used: number | null;           // latest input tokens / context limit
  active_model_m2: number | null;        // 0 = M1; 1 = M2
  advisor_progress: number | null;       // validated, sufficiently fresh scores
  advisor_stuckness: number | null;
  advisor_remaining_difficulty: number | null;
  advisor_confidence: number | null;
};

type RoutingObservation = {
  schema_version: "hecate.observation.v1";
  schema_hash: string;
  episode_id: string;
  checkpoint_id: string;
  sequence: number;
  identity: Identity;
  source: string;
  clock: string | null;
  checkpoint_verified: boolean;
  features: Features;                 // raw named measurements; null stays null
  feature_order: (keyof Features)[];  // exactly the 22 names above, in that order
  vector: number[];                  // length 22; transformed values or zero
  validity_mask: boolean[];          // length 22; same indices as vector
  action_mask: [boolean, boolean] | null;
  normalizer_hash: string | null;
  mode: "raw_diagnostic" | "normalized_diagnostic" | "router_ready";
};
```

`features` always retains raw measurements. `vector` holds raw or normalized
values according to `mode`; missing/disabled entries become numeric zero with
`validity_mask[i] = false`. Valid zero measurements have a true mask. Binary
`active_model_m2` passes through normalization unchanged. Action availability is
supplied by the controller and is not inferred from a missing-feature mask.

Historical traces with no controller action mask can produce diagnostic
observations. `router_ready` requires a frozen normalizer and explicit controller
context. No evaluator result, correctness label, reward, gold patch or advice
rationale is a feature in this schema.

#### 3. Frozen normalizer artifact

```typescript
type FrozenNormalizer = {
  version: "hecate.normalizer.v1";
  schema_hash: string;
  features: (keyof Features)[];       // same fixed feature order
  stats: Record<keyof Features, {
    mean: number;
    std: number;                     // population standard deviation
    count: number;                   // valid fitting observations for this feature
  }>;
  fitting_task_ids: string[];
  fitting_observations_hash: string;
  split_manifest_hash: string;
  hash: string;                      // hash of artifact excluding this field
};
```

A zero-count feature remains disabled. Zero variance uses the configured epsilon.
The matching schema hash pins the feature order, windows, missingness rules and
normalization configuration. Fitting IDs must belong to the explicitly designated
training set and must not intersect reserved IDs.

#### 4. Example observation

Illustrative raw observation after five completed interactions. The elapsed time,
visible-test measurements and advisor scores are unknown. `action_mask` is null
because this example represents a historical log without recorded controller
availability. The schema hash below is computed from the current v1 config.

```json
{
  "episode_id": "example-episode",
  "checkpoint_id": "example-checkpoint-5",
  "sequence": 22,
  "identity": {
    "run_id": "example-run",
    "task_id": "example-training-task",
    "session_id": "example-session",
    "harness": "codex",
    "harness_version": "pinned-build",
    "split": "train",
    "model_revision": null
  },
  "source": "example/gateway.jsonl",
  "clock": null,
  "checkpoint_verified": true,
  "features": {
    "completed_interactions": 5,
    "model_requests": 5,
    "transport_attempts": 6,
    "advisor_calls": 0,
    "request_budget_used": 0.125,
    "elapsed_s": null,
    "time_budget_used": null,
    "command_failure_rate": 0.2,
    "command_timeouts": 0,
    "repeated_errors": 0,
    "visible_passed": null,
    "visible_failed": null,
    "visible_pass_delta": null,
    "input_tokens": 500,
    "output_tokens": 50,
    "inference_s": 2.5,
    "context_used": 0.006103515625,
    "active_model_m2": 0,
    "advisor_progress": null,
    "advisor_stuckness": null,
    "advisor_remaining_difficulty": null,
    "advisor_confidence": null
  },
  "action_mask": null,
  "schema_version": "hecate.observation.v1",
  "schema_hash": "d8d81f862758b1e1ea7f1994d0b152518b728cdef919c5edf97192004a5ade33",
  "feature_order": [
    "completed_interactions",
    "model_requests",
    "transport_attempts",
    "advisor_calls",
    "request_budget_used",
    "elapsed_s",
    "time_budget_used",
    "command_failure_rate",
    "command_timeouts",
    "repeated_errors",
    "visible_passed",
    "visible_failed",
    "visible_pass_delta",
    "input_tokens",
    "output_tokens",
    "inference_s",
    "context_used",
    "active_model_m2",
    "advisor_progress",
    "advisor_stuckness",
    "advisor_remaining_difficulty",
    "advisor_confidence"
  ],
  "vector": [
    5.0,
    5.0,
    6.0,
    0.0,
    0.125,
    0.0,
    0.0,
    0.2,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    500.0,
    50.0,
    2.5,
    0.006103515625,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0
  ],
  "validity_mask": [
    true,
    true,
    true,
    true,
    true,
    false,
    false,
    true,
    true,
    true,
    false,
    false,
    false,
    true,
    true,
    true,
    true,
    true,
    false,
    false,
    false,
    false
  ],
  "normalizer_hash": null,
  "mode": "raw_diagnostic"
}
```


## Requirements

- **R1 — Reuse first:** Write a short reuse assessment identifying code retained,
  adapted or rejected and the logging gaps in the actual source artifacts.
- **R2 — Harness independence:** Support declared E7 and current harness formats
  through adapters; no model-specific State Builder. Unsupported versions fail
  explicitly and never silently change counter semantics.
- **R3 — Causality:** Build each observation from the episode prefix available at
  that checkpoint. Later outputs, final patches, hidden tests, gold fixes and
  independent evaluator outcomes cannot enter the observation.
- **R4 — Deterministic replay:** Same source artifacts, configuration and schema
  produce identical observation values/masks and checkpoint identities. Record
  tool-start/completion relationships and reject ambiguous causal ordering.
- **R5 — Honest missingness:** Unknown is distinct from zero. Do not reconstruct
  missing command exits, test results, tokens or timings from unsupported guesses.
- **R6 — Stable contracts:** Persist schema version/hash, feature order/units,
  normalizer hash, active-model mapping and separate action/feature masks.
- **R7 — Isolation:** Parse historical commands as data; never execute replayed
  commands. Keep evaluator-only files outside observation adapters and state input.
- **R8 — Reproducibility:** Replay artifacts record code commit, CLI/config,
  source hashes, selected training/pilot IDs, adapter versions, dependency versions,
  checkpoint coverage and rejection reasons. Preserve raw logs and failed records.
- **R9 — Durability:** Reuse existing checksum and off-Spark verification helpers
  for artifacts produced on Spark. No new storage service or credentials.
- **R10 — Scope:** No new model inference, advisor scoring, training, held-out
  evaluation, GPU workload or website deployment. Do not modify ongoing runs or
  their immutable source/config snapshots. Any integration run is separately scoped.

## Edge cases

- No commands, no visible tests or absent E7 session logging: features are masked.
- Duplicate/reordered events, reused session IDs or retries: avoid double counting;
  isolate episodes and preserve transport attempts independently of agent decisions.
- Batched/parallel tool calls: count individual completed interactions, but emit a
  checkpoint only at a verified safe boundary after all pending calls complete.
- Compaction: retain the audit ledger; record advice loss and observation freshness.
  Missing visible history cannot be treated as proof that a previous action vanished.
- Termination mid-window or a request/tool timeout: preserve termination and partial
  evidence; do not invent a final checkpoint or successful command completion.
- Malformed/truncated model output: retain its failure classification. It is not a
  completed tool interaction unless a command actually ran and completed.
- Clock changes or mixed clock sources: preserve ordering evidence; mask unreliable
  durations. Never report negative elapsed time as a valid feature.
- Test invocations with changed selection, working-tree conditions or identities:
  mark deltas noncomparable rather than interpreting them as progress.
- Missing advisor assessment, stale assessment or wrong schema/range: mask affected
  scores. Do not silently turn free-form E7 advice into invented scores.
- Unknown model role, schema mismatch or absent frozen normalizer: fail validation
  for router-ready output while retaining diagnostic replay evidence.
- Logs may contain untrusted text or sensitive data: never execute their contents
  or introduce credentials into artifacts; follow existing redaction conventions.

## Acceptance criteria

- [ ] Scott reviews the schema, checkpoint cadence, candidate features and scope
  before implementation; approval and changes are recorded here.
- [ ] Reuse assessment identifies actual available artifacts and optional-log gaps.
- [ ] Versioned event/schema configuration distinguishes requests, retries, tools,
  advisor calls, termination and evaluation-only data.
- [ ] Adapters replay at least one available E7 training/pilot trace and one current
  harness training/pilot trace; missing fields produce explicit coverage reports.
  If an E7 trace is unavailable, record the blocker rather than claim validation
  from synthetic fixtures alone.
- [ ] Collector and State Builder produce deterministic, causal observations with
  fixed feature order, units, masks, source references and checkpoint identities.
- [ ] Normalization fitting rejects reserved evaluation inputs and exports a
  reproducible frozen artifact, or raw-only mode is clearly identified as incomplete.
- [ ] Synthetic and saved-trace tests below pass without model inference or a GPU.
- [ ] Replay outputs and limitations are reviewable; Spark outputs have verified
  off-Spark copies. Existing experiment artifacts remain unchanged.

## Tests

1. **Counter semantics:** A fixture with two model decisions, a transport retry,
   three tool calls and duplicate completion events yields the correct distinct
   request/attempt/completed-interaction counts.
2. **Checkpoint safety:** Five completed interactions emit one logical checkpoint
   only at a safe boundary; a pending parallel call prevents early emission.
3. **Prefix isolation:** Appending later events, final evaluation labels or a gold
   patch cannot change any already emitted observation. Evaluator inputs are rejected.
4. **Missing versus zero:** No commands masks the failure rate; successful commands
   yield valid zero; partial token coverage masks full cumulative usage.
5. **Normalization:** Fit on explicit training IDs only; validate constant/all-missing
   features, stable feature order, frozen reload and rejection of held-out fitting.
6. **Visible-test comparability:** Comparable explicit test records yield correct
   deltas; missing/changing selections or unsupported text yield masked deltas.
7. **Advisor boundary:** Missing/stale/invalid scores are masked; E7 advice alone
   does not populate numeric scores; rationales and hidden outcomes stay out.
8. **Episode separation and clocks:** Interleaved sessions never mix features;
   ambiguous ordering and invalid elapsed durations are reported explicitly.
9. **Historical replay:** Compare adapter outputs to manually checked prefixes
   from the available E7/current training traces; retain discrepancy reports.
10. **Artifact integrity:** Source/config/schema hashes and observation checksums
    survive mirroring; incomplete copies fail verification.

## Decisions for review

1. Keep the proposed five-completed-interaction cadence? Include an initial routing
   decision, or begin decisions only after the first execution window?
2. Accept the proposed feature groups? Suggested first implementation: deterministic
   counters/usage and missingness first, with advisor slots masked until validated.
3. Should visible-test parsing enter v1, or remain masked until a reliable structured
   producer exists? Either choice must keep the schema and validity rules explicit.

## Implementation decisions — 2026-11-19

Approval accepts the proposed deterministic-first v1: cadence five, no initial decision; advisor slots masked until validated; visible tests require structured comparable records and historical stdout is not parsed. Raw replay is diagnostic; router-ready output requires frozen normalization and explicit controller action masks. No inference or active-run changes.
