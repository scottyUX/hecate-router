# Telemetry Collector

Status: implemented and verified offline in TASK-004. Live event collection and
routing integration remain pending.

The collector turns execution events into deterministic measurements at safe
routing checkpoints. It measures observed behavior; it does not decide whether
the task is correct or whether to escalate.

```mermaid
flowchart LR
    A[Saved execution logs] --> B[Versioned adapters]
    B --> C[Canonical events]
    C --> D[Telemetry Collector]
    D --> E[Checkpoint measurements]
    E --> F[State Builder]
```

## Code and interfaces

- [Event contract](../../src/hecate/telemetry/events.py): `Event` and schema version
  `hecate.events.v1`.
- [Adapters](../../src/hecate/telemetry/adapters.py): declared source formats.
- [Collector](../../src/hecate/telemetry/collector.py): `Collector(config)`,
  `push(event)` and `collect(events, config)`.
- [Configuration](../../configs/routing_observation.yaml): cadence, windows,
  signature rule and advisor freshness.

`push(event)` returns a raw observation dictionary when a checkpoint is eligible,
or `None` otherwise. `collect(...)` returns all eligible observations from a stream.
Each episode has separate state; interleaved sessions do not share counters.

## Inputs

Canonical events identify their run, task, session, episode, source and sequence.
The event's `kind` selects a payload for requests, responses, tool actions,
controller context, optional assessments/tests, boundaries or termination.

Supported replay formats:

- `canonical-v1`: explicit canonical event records.
- `hecate-codex-v1`: gateway logs and per-request metrics. Correlated tool outputs
  already visible in the next request establish the preceding execution history.
- `hecate-mini-v1`: native formatted command observations in saved request histories.
- `e7-session-v1`: coarse initialization/advice/step batches; diagnostic conversion
  only, because individual tool completions and safe boundaries are unverified.
- `e7-proxy-v1`: request/response/advice records; proxy-only logs do not establish
  tool checkpoints.

Adapters parse logs as data. They never execute recorded commands, import a mutable
advisor-models checkout or read independent evaluator results into observations.

## Measurements

The collector keeps these quantities separate:

- Model requests: agent decisions to query the coding model.
- Transport attempts: requests plus transport retries, when fully recorded.
- Completed interactions: distinct completed tool calls.
- Advisor calls: separately recorded advisor activity.

It also computes request-budget usage, episode time when the start/clock is known,
recent command failures/timeouts/repeated errors, usage/context measurements and
optional validated assessment or visible-test features.

```text
request_budget_used = model_requests / request_limit
command_failure_rate = failed_completed_commands / completed_commands_in_window
context_used = latest_input_tokens / context_limit
```

The command window is the latest five completed shell commands. A valid zero
failure rate means commands actually completed successfully. With no commands,
unknown exits or an invalid denominator, the relevant measurement is `null`.

Error signatures use `stderr-whitespace-v1`: explicit error evidence has whitespace
normalized; repeated signatures count duplicates beyond their first occurrence.
A nonzero exit alone does not provide an error signature. Historical Codex logs
without explicit timeout evidence keep timeout status unknown, except exit 124.

Cumulative token and inference totals require complete coverage of the requests
at that checkpoint. Cached input is not added again to an inclusive input count.
Missing usage is not replaced with zero or inferred from unrelated totals.

## Checkpoint behavior

The default cadence is five completed interactions, with no initial routing
decision. A checkpoint can be emitted only at an explicit verified boundary before
the next model request when:

1. Every observed model request has a corresponding response/failure record.
2. No correlated tool call remains pending.
3. At least five additional interactions completed since the previous checkpoint.
4. The source establishes reliable episode ordering.

If several tools complete together, the checkpoint waits for the next safe boundary;
it is not inserted into the middle of a parallel batch. Termination does not create
an extra routing decision. Unverified historical boundaries produce no observation.

Duplicate event IDs with identical contents are ignored. Conflicting duplicates,
changed episode identity or nonincreasing episode sequence are rejected. Duplicate
completed-tool notifications are also correlated by tool ID.

## Output

A raw checkpoint record contains:

```text
episode_id, checkpoint_id, sequence, identity, source, clock,
checkpoint_verified, features, action_mask
```

`features` is the named set of 22 raw measurements. Unknown fields remain `null`.
The action mask comes from explicit controller context and remains separate from
feature validity. The [State Builder](state-builder.md) validates and transforms
this record into the numeric observation contract.

The [complete event and observation schemas](../tasks/e7-telemetry-and-routing-state-builder.md#concrete-schemas--v1)
include field types, payload contracts and a full JSON example.

## Optional test and advisor signals

Visible test deltas require explicit test IDs and matching selection, conditions
and parser identities. Arbitrary command stdout is not parsed as correctness.
Changing those conditions masks the delta.

Advisor scores require `schema = hecate.assessment.v1`, `validated = true`, values
in `[0, 1]`, and sufficient freshness. Scores expire after more than five subsequent
completed interactions. E7 free-form advice does not automatically populate scores.
Final evaluation labels, reward and gold patches have no observation input type.

## Running replay

From the repository root, after restoring the source artifacts listed in the
[input manifest](../../configs/telemetry/task004_replay_inputs.json):

```bash
PYTHONPATH=src python scripts/replay_routing_observations.py \
  --inputs configs/telemetry/task004_replay_inputs.json \
  --output-root data/outputs/runs --run-id telemetry-replay-example-01
```

Use a new run ID. Output includes canonical events, observations, coverage/gaps,
source hashes, config/code snapshots and checksums. No model inference or GPU is
required. See the [runbook](../tasks/task-004-reuse-and-runbook.md) for artifact
restoration, normalization and mirror verification.

## Verification and limits

TASK-004 has 45 passing targeted checks, including 12 telemetry/state tests.
Real replay covered an E7 training/pilot log and two current Codex training traces.
The E7 batch reported eight agent steps but yielded zero invented checkpoints.
Each current trace yielded one verified observation; independently checked
interaction/request counts were `(5, 5)` and `(5, 6)`.

This implementation replays existing evidence. It does not add live pause/resume,
complete asynchronous-session correlation, model switching, new structured test or
advisor producers, a reward service, or a routing policy. Missing historical
measurements and outputs after the last captured request are not reconstructed.
