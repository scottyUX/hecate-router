# Saved-source patch evaluator

Protocol: `source-patch-v2`, introduced by TASK-007 after auditing TASK-006.

## What the results mean

`resolved` answers whether the saved source patch passes the independent required
tests. It is true/false only after valid evaluator controls and a completed grade;
otherwise it is null. It does not depend on an agent's final response or exit.

`session_completed` records a normal agent completion. `termination_reason`
retains a context/request/time/output limit or execution failure. `policy_compliant`
records whether protected test/config files were changed. `clean_success` requires
correctness, normal completion and policy compliance together. Report each axis.

## Evaluation flow

1. Run gold-patched and unpatched controls in fresh, isolated Docker containers.
   Hidden tests are restored only in the evaluator, never in the agent workspace.
2. Collect the agent's complete patch against the recorded original base commit.
   Preserve that raw patch and the agent logs, even after a session failure.
3. Make a separate `evaluation.diff`. Exclude only newly added protected test/config
   files, recording their names and both patch hashes in `patch_projection`.
   Existing protected file edits/deletes and unsupported/unsafe patch structures
   produce an explicit projection failure with unknown correctness.
4. Apply the evaluation patch to a fresh evaluator workspace and run the required
   tests. Missing outcomes or evaluator setup errors remain unknown. Import or
   collection errors caused by the source patch after successful controls are failures.
5. Save correctness, termination, policy and clean-success outcomes independently.

Added tests are never executed by the independent evaluator. No source hunks are
repaired, and a correct patch does not remove a policy violation or server failure.
The strict fixture gates and sandbox protections are unchanged.

## Budget and infrastructure accounting

New gateway records distinguish request caps and explicit context-length HTTP400
errors from server/transport/protocol errors. The final classification is retained
even if the Codex process exits before the controller observes the stop condition.
Context/request budgets do not count toward consecutive infrastructure errors.
Genuine infrastructure errors still count even if their saved patches pass.

Old HTTP400 records that lack response bodies cannot be reclassified automatically
from status alone. The old TASK-006 server log audit identifies context limits, but
the production replay conservatively preserves classifications without that evidence.

## Regrading without new attempts

Use the original config and selection with the normal Codex runner's
`--reuse-agent-from <original-run>` and a fresh `--run-id`. The runner validates
the source run's checksums and config, copies existing agent artifacts, and reruns
controls and grading. Missing saved attempts fail closed; no replacement inference
is allowed. The manifest records zero new model attempts and the source run.

Historical agent faults do not stop a grading-only replay; new evaluator
infrastructure failures still trigger the halt rule. Original run files and labels
are never overwritten. Every replay retains code/config snapshots and checksums
and must be copied and verified off Spark.

## Comparing runs

Do not compare the old policy-gated `resolved` scores directly to v2 correctness.
Regrade both arms under the same protocol. The paired summary tool rejects mixed
protocols. Always state that the TASK-006 sample is20 selected E7 training tasks,
not a held-out SWE-bench result.
