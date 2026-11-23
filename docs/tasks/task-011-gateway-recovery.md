# TASK-011 — Gateway recovery and fresh ten-task validation

Scott authorized recovery for unknown tool calls and reasoning-only responses,
testing before inference, then a fresh attempt on the same TASK-010 ten IDs.
Preserve every TASK-010 artifact; TASK-011 is a new protocol and run namespace.
Do not combine its results with earlier attempts as a single success estimate.

Requirements: opt-in gateway recovery, unchanged legacy behavior by default.
Reject an unknown action without executing it or translating it into another
tool. Preserve its name/arguments, return an explicit tool error to the model
with the available tool names, then request a valid action. Do not expose the
unknown action to Codex, where a removed but implemented tool might execute.
For a stop response containing only reasoning, retain the raw response in logs
and ask for an action or final answer. Never promote reasoning to final text.
Each continuation consumes one ordinary model request, records usage and wall
time, and obeys the shared cap. Permit at most three recoveries per Codex
request; repeated invalid output stops explicitly. No recovery from output
truncation, malformed JSON, escalation requests, or transport failure by this
mechanism. Transport retries retain their existing separate policy.

Test acceptance: deterministic unknown-tool then valid action, reasoning-only
then valid action, genuine final answer, repeated-invalid recovery limit,
shared request cap, raw traces/usage retention, no unknown action execution,
and legacy behavior unchanged. Then use actual Codex in the existing isolated
fixture with injected initial responses to verify its complete tool round-trip,
followed by native Qwen read/edit/test-repair and patch-tool gates before tasks.

Run the same frozen ten IDs, one fresh model attempt each, under task011 run
IDs and separate root/config snapshots. Keep model checkpoint, BF16, sampling,
262144 context, 8192 output cap and task budgets unchanged. Record gateway
recovery enabled and its three-recovery bound. Pin pip==24.0 in scikit-learn's
environment to retain its official --no-use-pep517 recipe. Keep the original
recipe and pin in the test spec; require clean reference-patch controls.
Astropy's exact build-pin check and Pylint's narrow baseline exception remain.
Candidate missing outcomes remain unknown. Do not replace tasks on failures.

Persist exact code/config/dependencies, attempts, raw outputs, patches and test
reports. Run two five-task batches with verified off-Spark checkpoint copies;
stop on failed gates/controls and report unknowns separately from unsolved
patches. Stop only owned servers on exit. No training telemetry or API spend.
