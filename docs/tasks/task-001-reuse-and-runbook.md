# TASK-001 implementation and runbook

## Reuse assessment

The existing E7 integration was inspected in `/Users/scottdavis/advisor-models`:
`codex_proxy.py`, `eval_codex.py` and `tests/test_codex_proxy.py`. The Spark E10
checkout reports commit `ea6575a5cf12580d0385f3ac13987ae4540623b3`.

- **Adapted:** the Codex custom-provider configuration and embedded model-catalog
  extraction approach from `eval_codex.py`, with explicit no-reasoning/context
  overrides and a task-specific instruction file. The upstream project is
  Apache-2.0; its license is retained at
  `docs/licenses/advisor-models-APACHE-2.0.txt`.
- **Reused as design patterns:** model-request caps, structured JSONL evidence,
  independent patch grading and patched/unpatched controls. These are newly
  implemented in Hecate, with offline fixtures.
- **Rejected:** OpenRouter/API-key routing, advice insertion, host-network agent
  containers, shared mutable checkout dependencies, zero-filled missing token
  counts and evaluator errors silently converted to failed tasks.
- **Evaluator:** invoke pytest in an evaluator-only copy of the pinned ARM
  Tenacity image. Restore evaluator tests there, reverse the injected bug for
  the gold control, and check every named FAIL_TO_PASS/PASS_TO_PASS outcome.
  Missing test results or runner errors are infrastructure failures.

No runtime import depends on advisor-models. Its existing training dataset is an
explicit input verified against the preselected hash. No source from E10 is
modified, and its serving/training resources are not reused or stopped.

## Modules

- `model_gateway.py`: Responses/Chat translation, fixed local upstream,
  bounded transport retries, usage logs and valid Responses SSE output.
- `codex_session.py`: pinned Codex metadata/configuration, process limits and
  JSONL lifecycle interpretation.
- `codex_relay.py`: stdlib-only relay inside a networkless agent container.
  It exposes only the task-owned Unix inference socket over container loopback.
- `task_environment.py`: disposable containers, clean one-commit task trees,
  patch capture, source-only policy and separate grading.
- `codex_artifacts.py`: new attempt directories, manifest/source/config
  snapshots, checksums and an explicit off-Spark verification receipt.
- Existing `hecate.execution` exports are lazy to keep this CPU-side runner
  independent of the unrelated datasets/SWE-bench loading stack.

## Effective interface

Automatic tool-call formatting failed in the initial Qwen diagnostics. The
accepted candidate configuration therefore uses schema-constrained function
selection (`tool_choice=required`) with a declared `hecate_finish(response)`
action mapped to a Codex final message. It does not parse or execute commands
printed in prose. The model still chooses which allowed action to take and all
arguments; the adapter does not choose the solution for it.

The first patch-tool fixture failed: Qwen did not follow Codex's custom patch
syntax. The allowed fallback is explicitly pinned as `editing_mode: shell`.
The upstream tool list excludes `apply_patch`, user-input, images and other
unsupported tools. Shell escalation options are removed from advertised schemas;
forged escalation calls are rejected. Shell commands execute under a 120-second
`timeout` wrapper inside the disposable container.

Agent containers run as the calling unprivileged UID, with no network, a read-only
root filesystem, dropped capabilities, no Docker socket and no host home mount.
They can write only their task tree and bounded temporary storage. The only
mounted service is the inference Unix socket. Source history is replaced with a
single task-base commit, mounted read-only alongside protected test files. Hidden checks and bug-fix metadata stay outside the agent.

## Setup on Spark

Read `docs/SPARK_GUIDE.md` first. Check active containers, GPU processes, memory,
disk and ports. Do not interrupt other jobs. Use a task-owned working directory
such as `~/work/hecate-task001`; put only the required Hecate source/configuration
there rather than copying unrelated local changes into shared checkouts.

```sh
python3 -m venv ~/work/hecate-task001/venv
~/work/hecate-task001/venv/bin/pip install -r configs/codex_compat_requirements.txt
```

The approved bootstrap script requires `huggingface_hub` and PyYAML in an existing
bootstrap environment. It verifies the exact npm ARM package's SHA-512 integrity
and downloads the fixed Hugging Face model revision into the task-owned cache:

```sh
python scripts/setup_codex_qwen7b.py --root ~/work/hecate-task001
python scripts/serve_codex_qwen7b.py --root ~/work/hecate-task001
```

Use the task runner venv for the commands below, with `PYTHONPATH=src` and
`HECATE_CODE_SHA` set to the source commit. The manifest also snapshots source
files so uncommitted integration iterations remain inspectable. Run long commands
in a uniquely named tmux session, redirecting output to a task-owned log file.

```sh
python scripts/run_codex_baseline.py fixtures \
  --root ~/work/hecate-task001 --run-id task001-fixtures-<new-attempt>

# Only after fixture and isolation gates pass:
python scripts/run_codex_baseline.py smoke \
  --root ~/work/hecate-task001 --run-id task001-smoke-<new-attempt> \
  --fixtures-run ~/work/hecate-task001/runs/task001-fixtures-<passing-attempt> \
  --dataset /path/to/train_jd__tenacity.json
```

The runner requires a matching passing `--fixtures-run` before benchmark execution.
It refuses non-ARM Linux live execution, dataset checksum mismatches and
existing attempt directories. It has no general sweep mode. Model serving itself
is separate so that the same server can handle the short fixture/smoke sequence;
stop and remove only `hecate-task001-model` after that work finishes.

## Verification

```sh
.venv/bin/python -m pytest tests/test_codex_compatibility.py tests/test_execution.py -q
```

Copy every attempt off Spark, including failed attempts, with `rsync`. Verify the
received files against `checksums.json`, then compare a second local destination
using `verify_mirror(source, destination, off_spark=True)`. The resulting
`sync_receipt.json` is the durable-copy attestation; a manifest awaiting copy alone
does not mean the run is complete. Keep the copies under gitignored
`data/outputs/runs/`; commit the human-readable compatibility report, not raw data.

A larger baseline, advisor, M2, PPO and website deployment remain out of scope.

To continue an interrupted grading sequence without repeating model attempts,
use `--reuse-agent-from <completed-partial-run>`. The source run must match the
configuration and pass checksum validation. Saved agent artifacts are copied
unchanged; their patches are re-evaluated, while tasks with no saved agent attempt
are run once. Agent exit status and evaluator exit status are recorded separately.
