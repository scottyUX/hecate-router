# TASK-004 — Reuse assessment and replay runbook

## Implemented scope

Branch: `codex/task-004-telemetry-state-builder`.

The implementation is entirely offline: adapters, canonical events, causal counters,
22-feature observations, train-only normalization and an immutable replay CLI.
No inference, GPU job, live routing switch or PPO training is introduced.

State construction lives in `src/hecate/telemetry/state.py` alongside its event
contract and collector. This avoids importing the existing router training package
and its dataset/backbone dependencies just to replay logs. The original task's
module paths were proposals, subject to the reuse assessment.

## Reuse assessment

Inspected E7 source in the advisor-models checkout at
`2403225282d2dc74e3cb7db77529f4d15580630d`. This is the inspected checkout's
revision, not a claim about the older log producer's exact revision.

- `agent_server.py`: adapt initialization/advice/step record semantics. Preserve
  the legacy step fields. Do not convert a batch's cumulative step count into
  individual tool completions or safe routing checkpoints.
- `codex_proxy.py`: adapt request/response usage and advice event semantics.
  A proxy-only E7 log lacks correlated tools; it cannot produce verified routing
  observations. No OpenRouter forwarding, pricing or advice insertion is copied.
- `eval_swe_smith.py` and `eval_codex.py`: inspect artifact organization and
  counters only. Their evaluator results, patches and correctness labels are
  outside observation input.
- Current `model_gateway.py`: reuse the existing gateway logs and model-request
  metrics. Correlate function outputs already visible in the next request; do not
  merge untimestamped Codex events with gateway records by guessed timing.
- Current mini harness: adapt native formatted observations visible in model
  request histories. Format-error feedback is not an executed command.
- `codex_artifacts.py`: directly reuse immutable run creation, checksums and
  verified mirror helpers. No new storage/authentication implementation.

There is no runtime import from the sibling advisor-models checkout and no command
execution during replay. Adapters recognize explicit format versions.

## Real trace inventory

The E7 training/pilot trace was retrieved from the existing artifact bucket after
GCP authentication was refreshed. Exact URI and SHA-256 are recorded in
`configs/telemetry/task004_e7_source.json`.

- E7 `pr_425`: three records (initialization, advice feedback, one completed batch),
  reporting eight cumulative agent steps. Its missing request/tool correlation
  means **zero verified routing checkpoints**, explicitly reported as a coverage
  limitation. The raw log is retained locally under ignored `data/outputs/`.
- TASK-002 7B `combine_module__yjmtlc2r` and
  `func_pm_ctrl_shuffle__3ljvivv1`: saved training-task agents, eight captured
  request boundaries each. Replay yields one verified observation per trace at
  the configured five-completed-interaction cadence.

Model usage can be recovered for these current traces. Actual episode-start time,
controller action availability, structured visible tests, reliable timeout/error
signatures and validated advisor assessments are absent and remain masked.
History after the final captured model request is not inferred. Asynchronous tool
sessions without a fully correlated completion remain pending conservatively.

## Replay

Run from the repository root in an environment with the existing PyYAML dependency.
No package or environment changes are required.

Retrieve the E7 source if it is absent (existing GCP access required):

```bash
mkdir -p data/outputs/task004-inputs
python - <<'PY'
import json, subprocess
from pathlib import Path
source = json.loads(Path('configs/telemetry/task004_e7_source.json').read_text())
subprocess.run(['gcloud', 'storage', 'cp', source['uri'],
                'data/outputs/task004-inputs/e7-session.jsonl'], check=True)
PY
```

The current trace paths are in `configs/telemetry/task004_replay_inputs.json`;
they refer to the checksum-mirrored TASK-002 artifacts on this laptop. Restore
those original run artifacts before replaying on another machine.

Raw diagnostic replay:

```bash
PYTHONPATH=src python scripts/replay_routing_observations.py \
  --inputs configs/telemetry/task004_replay_inputs.json \
  --output-root data/outputs/runs --run-id task004-replay-raw-01
```

Fit an example normalizer using only the explicitly named training traces:

```bash
PYTHONPATH=src python scripts/replay_routing_observations.py \
  --inputs configs/telemetry/task004_replay_inputs.json \
  --output-root data/outputs/runs --run-id task004-replay-normalized-01 \
  --fit-split configs/telemetry/task004_normalization_split.json
```

The sample split manifest contains no reserved IDs because every input here is
explicitly a training/pilot log. Full routing experiments must supply their own
complete training/reserved split manifest. A normalizer fitted on these two
observations is a contract demonstration, not a selected production artifact.

`--normalizer <frozen.json>` loads a hash-checked artifact instead of fitting.
`--router-ready` additionally requires explicit controller action masks and model
context. Historical logs above intentionally fail this gate. Canonical event
input supports structured controller/test/assessment records for offline fixtures;
this task does not claim their live producers have been implemented.

Each run stores input/config/source snapshots, event and observation JSONL,
source hashes, coverage limitations, optional normalizer, manifest and checksums.
Use a new run ID; existing outputs are never overwritten. Shared artifact helpers
label runs awaiting a mirror until a separate verified synchronization receipt
exists. Local replay requires no Spark copy; an additional verified local mirror
is used for the completion evidence.

## Validation

Targeted tests cover duplicate and interleaved events, safe boundaries with pending
calls, future/evaluator exclusion, unknown versus valid zero, partial usage,
clock uncertainty, visible-test comparability, stale/invalid advisor scores,
training-only normalization, artifact hashes, schema mismatches and action gating.
Real traces are replayed separately from synthetic unit fixtures.

See the TASK-004 definition for the complete schemas and acceptance criteria.
