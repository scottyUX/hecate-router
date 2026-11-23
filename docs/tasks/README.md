# Implementation tasks

Each task defines its name, description, specifications, requirements, edge cases,
acceptance criteria and tests before implementation. Scott reviews it first;
approval, amendments and completion evidence remain with the task.

## TASK-001 — Qwen2.5-Coder-7B with Codex on Spark

Status: completed with declared compatibility limitations; three-task smoke 0/3.

- [Task and approval record](qwen25-coder-7b-codex-spark-compatibility.md)
- [Reuse assessment and runbook](task-001-reuse-and-runbook.md)
- [Compatibility report](task-001-compatibility-report.md)

TASK-001 itself does not authorize a larger baseline or PPO routing; follow-up authorization is recorded in its own task below.

## TASK-002 — Paired 20-task Qwen2.5-Coder 7B / 14B pilot

Status: authorized; fixed protocol and selection recorded before inference.

- [Task, requirements and acceptance criteria](qwen25-coder-7b-vs-14b-codex-20-task-pilot.md)

Same 20 fresh training tasks and harness for both models, run sequentially on Spark.

- [TASK-003: 7B mini-SWE-agent harness control](qwen25-coder-7b-mini-swe-agent-pilot.md) — same 20 tasks, parallel quality diagnostic.

## TASK-004 — E7 telemetry reuse and routing State Builder

Status: completed offline implementation and replay validation on `codex/task-004-telemetry-state-builder`.

- [Task, specifications, requirements, edge cases, acceptance criteria and tests](e7-telemetry-and-routing-state-builder.md)

Reuse E7/current harness events to produce causal, versioned routing observations.

- [TASK-004 reuse assessment and replay runbook](task-004-reuse-and-runbook.md)

## TASK-012 — Qwen3.6 + Codex on the full SWE-bench-45

Status: draft for review; no code or model calls.

- [Task, protocol, decisions and acceptance criteria](task-012-qwen36-swebench45.md)

All 45 tasks × 4 attempts, compared with arXiv:2610.32483v1 Tables 13/14/30.
