#!/usr/bin/env python3
"""Create Hecate Stage 1 backlog issues on GitHub."""

from __future__ import annotations

import json
import subprocess
import sys

REPO = "scottyUX/hecate"

INVARIANTS_SHARED = """\
- **Shared scaffold:** identical issue text, file context, and prompt for every model; only the model slug varies.
- **Single-shot (v1):** one prompt → one patch; no multi-turn agent loop.
- **Full counterfactual matrix:** persist raw outcomes for every (task, model) pair.
- **Rich storage:** record raw patch + metadata; defer label scheme to Stage 3.
- **Reproducibility:** every run writes a manifest with config, slugs, timestamp, git commit, cost."""

ISSUES = [
    {
        "id": "S1",
        "title": "S1 · Initialize repository",
        "milestone": "M0 — Project setup",
        "labels": ["stage-1", "setup"],
        "body": f"""## Scope
Create `README.md` (project one-pager + Stage 1 scope), `LICENSE`, `.gitignore`, dependency manifest, and the directory tree from the kickoff brief §6.

## Done when
Repo clones, structure matches §6, README explains how to run the pilot (even before code exists).

## Invariants
{INVARIANTS_SHARED}

## Dependencies
None — first task.
""",
    },
    {
        "id": "S2",
        "title": "S2 · Environment & dependencies",
        "milestone": "M0 — Project setup",
        "labels": ["stage-1", "setup", "infra"],
        "body": f"""## Scope
Python env; pin `swebench`, an OpenRouter/HTTP client, `pyyaml`, `python-dotenv`, a diff/patch library, and a test runner. Add `.env.example`.

## Done when
A fresh checkout installs cleanly and loads the API key from `.env`.

## Invariants
Never commit secrets. OpenRouter API key lives in local `.env` (gitignored); commit only `.env.example`.

## Dependencies
Depends on S1.
""",
    },
    {
        "id": "S3",
        "title": "S3 · Data loading & canonical schema",
        "milestone": "M0 — Project setup",
        "labels": ["stage-1", "infra"],
        "body": f"""## Scope
Load SWE-bench Lite; implement the per-(task, model) record schema (§7) with append-friendly Stage-2 fields.

Canonical fields per record:
- `instance_id`, `repo`, `base_commit`
- `model_slug`, `tier` (`small` | `large`)
- `prompt` (or hash + pointer), `context_files`
- `raw_response`, `extracted_patch`, `patch_parse_ok`
- `prompt_tokens`, `completion_tokens`, `cost_usd`
- `decoding_params`, `timestamp`, `run_id`
- Stage 2 placeholders: `patch_applied`, `fail_to_pass`, `pass_to_pass`

## Done when
All 300 instances load; one record can be created, serialized, and re-read losslessly.

## Invariants
{INVARIANTS_SHARED}

## Dependencies
Depends on S2.
""",
    },
    {
        "id": "S4",
        "title": "S4 · Confirm model slugs & pricing (config)",
        "milestone": "M0 — Project setup",
        "labels": ["stage-1", "cost", "needs-verification"],
        "body": """## Scope
Verify the four Option A models' exact OpenRouter slugs and current per-token prices; write them into `configs/option_a.yaml` with tiers and the budget/ceiling.

Models to verify:
- Qwen 2.5 72B (large)
- Llama 3.3 70B (large)
- Qwen 2.5 7B (small)
- Llama 3.1 8B (small)

## Done when
Config lists verified slugs + prices; a dry-run cost estimate for 1,200 samples is computed and recorded.

## Invariants
Do not assume slugs or prices — confirm against OpenRouter's live model list before any spend.

## Dependencies
Depends on S1.
""",
    },
    {
        "id": "S5",
        "title": "S5 · Oracle/BM25 context builder",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "scaffold"],
        "body": f"""## Scope
From a task, derive the target file(s) (oracle: from gold patch; or BM25) and load their contents at `base_commit`. Identical method for all models.

## Done when
Given an `instance_id`, returns the file context deterministically; method is config-selectable (`oracle` | `bm25`).

## Invariants
- **Oracle / retrieval context:** same context-building method across all models.
- **Shared scaffold:** context must not vary per model.

## Dependencies
Depends on S3.
""",
    },
    {
        "id": "S6",
        "title": "S6 · Prompt template",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "scaffold"],
        "body": f"""## Scope
One template: issue text + file context → instruction to output a single unified diff. Frozen and versioned.

## Done when
Template renders for any instance and is identical across models.

## Invariants
- **Shared scaffold:** every model receives the identical prompt/instructions.
- **Single-shot (v1):** one prompt → one patch.

## Dependencies
Depends on S5.
""",
    },
    {
        "id": "S7",
        "title": "S7 · OpenRouter client wrapper",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "generation", "infra"],
        "body": """## Scope
HTTP client with timeout, retry/backoff, bounded concurrency, and capture of token usage per call.

## Done when
A single call returns text + token counts; transient failures retry; concurrency is capped.

## Invariants
- **Reproducibility:** fixed decoding params, recorded per call.

## Dependencies
Depends on S2, S4.
""",
    },
    {
        "id": "S8",
        "title": "S8 · Patch extraction & normalization",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "generation"],
        "body": f"""## Scope
Parse model output into a clean unified diff: strip markdown fences, validate diff structure, flag unparseable outputs (`patch_parse_ok=false`) rather than crashing.

**Note:** Coordinate patch format with Stage 2 apply step early (see E-M3 epic) to avoid format mismatch.

## Done when
On a sample of raw outputs, valid diffs are extracted and malformed ones are flagged, not fatal.

## Invariants
- **Rich storage:** even malformed responses get stored — they are data about model behavior.
- Do not discard raw outputs.

## Dependencies
Depends on S6.
""",
    },
    {
        "id": "S9",
        "title": "S9 · Caching layer",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "infra", "cost"],
        "body": """## Scope
Content-hash key per (instance, model, prompt-version); skip if cached. Cache survives crashes/restarts.

## Done when
Re-running a completed task makes zero API calls.

## Invariants
No tolerance for accidental re-runs — caching is load-bearing for the ~$38 budget target.

## Dependencies
Depends on S3, S6.
""",
    },
    {
        "id": "S10",
        "title": "S10 · Cost tracker & hard budget guard",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "cost"],
        "body": """## Scope
Maintain a running cost total; refuse to start a call that would exceed the ceiling ($100 hard limit); persist the total across restarts.

## Done when
A simulated over-budget run halts gracefully before exceeding the ceiling and logs why.

## Invariants
Budget target ≈ $38 for 1,200 samples; hard ceiling $100.

## Dependencies
Depends on S4, S7.
""",
    },
    {
        "id": "S11",
        "title": "S11 · Generation runner (orchestrator)",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "generation"],
        "body": f"""## Scope
Tie S5–S10 together: iterate (task × model), resumable, writes records + a run manifest.

## Done when
`scripts/run_pilot.py` runs end-to-end on 1 task.

## Invariants
{INVARIANTS_SHARED}

## Dependencies
Depends on S5, S6, S7, S8, S9, S10.
""",
    },
    {
        "id": "S12",
        "title": "S12 · Run the pilot (20 tasks × 1 model)",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "pilot"],
        "body": """## Scope
Execute the runner on 20 tasks with one small model. Manually inspect a few patches.

## Done when
20 records produced; patches are human-readable diffs; cost-per-sample and per-task wall-clock recorded.

## Invariants
- **Day 2 gate:** if patches don't parse/produce by day 2, stop and debug scaffold rather than pushing forward.

## Dependencies
Depends on S11.
""",
    },
    {
        "id": "S13",
        "title": "S13 · Pilot report & go/no-go",
        "milestone": "M1 — Pilot (20 tasks)",
        "labels": ["stage-1", "pilot", "docs"],
        "body": """## Scope
Summarize: fraction of patches that parse cleanly, extrapolated cost for the full sweep, estimated wall-clock, and any red flags.

**Gate:** proceed to M2 only if the pilot is clean.

## Done when
A short report exists with a clear go/no-go recommendation; shared with advisors.

## Open question for advisors
Label scheme for Stage 3 — binary "escalate?" vs. multiclass "cheapest-resolver." Defer until pilot reveals small/large solve-rate split.

## Dependencies
Depends on S12.
""",
    },
    {
        "id": "S14",
        "title": "S14 · Full generation sweep (4 × 300)",
        "milestone": "M2 — Full sweep (1,200 patches)",
        "labels": ["stage-1", "generation", "cost"],
        "body": """## Scope
Run all four verified models across all 300 tasks with caching + budget guard active.

## Done when
Up to 1,200 records exist; total cost within ceiling; run is resumable if interrupted.

## Invariants
- **Full counterfactual matrix:** every (task, model) pair must be accounted for.

## Dependencies
Depends on S13 go/no-go approval.
""",
    },
    {
        "id": "S15",
        "title": "S15 · Output validation",
        "milestone": "M2 — Full sweep (1,200 patches)",
        "labels": ["stage-1", "infra"],
        "body": """## Scope
Verify completeness (every (task, model) accounted for, missing/failed ones logged), schema validity, and that the full counterfactual matrix is intact.

## Done when
A validation script passes and reports coverage + parse rate + total cost.

## Dependencies
Depends on S14.
""",
    },
    {
        "id": "S16",
        "title": "S16 · Stage-1 handoff artifact",
        "milestone": "M2 — Full sweep (1,200 patches)",
        "labels": ["stage-1", "docs"],
        "body": """## Scope
Package the records + manifest for Stage 2; write a short doc describing the schema and how to load it.

## Done when
Stage 2 can read the outputs without touching Stage 1 code.

## Dependencies
Depends on S15.
""",
    },
    {
        "id": "E-M3",
        "title": "E-M3 · Execution & labels (epic)",
        "milestone": "M3 — Execution & labels",
        "labels": ["downstream"],
        "body": """## Scope (placeholder)
Stage 2: Docker execution harness — apply patches and run tests. Stage 3: construct routing labels from execution outcomes.

Do not break down into sub-tasks yet.
""",
    },
    {
        "id": "E-M4",
        "title": "E-M4 · Router training (epic)",
        "milestone": "M4 — Router training",
        "labels": ["downstream"],
        "body": """## Scope (placeholder)
Stage 4: Fine-tune DistilBERT-class encoder router on execution-grounded labels.

Do not break down into sub-tasks yet.
""",
    },
    {
        "id": "E-M5",
        "title": "E-M5 · Evaluation (epic)",
        "milestone": "M5 — Evaluation",
        "labels": ["downstream"],
        "body": """## Scope (placeholder)
Stage 5: Evaluate router vs. baselines (always-small, always-large, oracle routing).

Do not break down into sub-tasks yet.
""",
    },
    {
        "id": "E-M6",
        "title": "E-M6 · SDLC adaptation (epic)",
        "milestone": "M6 — SDLC adaptation",
        "labels": ["downstream"],
        "body": """## Scope (placeholder)
Staged domain adaptation: fine-tune router on AI-usage data from undergraduate SDLC course.

Do not break down into sub-tasks yet.
""",
    },
]


def gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    existing_titles = {
        i["title"]
        for i in json.loads(gh("issue", "list", "--repo", REPO, "--limit", "100", "--json", "title"))
    }

    created: list[tuple[str, int, str]] = []
    for issue in ISSUES:
        if issue["title"] in existing_titles:
            num = json.loads(
                gh(
                    "issue", "list", "--repo", REPO,
                    "--search", issue["title"], "--json", "number",
                )
            )[0]["number"]
            print(f"SKIP {issue['id']}: #{num} (exists)")
            created.append((issue["id"], num, issue["title"]))
            continue

        label_args = []
        for label in issue["labels"]:
            label_args.extend(["--label", label])

        url = gh(
            "issue", "create",
            "--repo", REPO,
            "--title", issue["title"],
            "--body", issue["body"],
            "--milestone", issue["milestone"],
            *label_args,
        )
        num = int(url.rstrip("/").split("/")[-1])
        print(f"CREATE {issue['id']}: #{num} {url}")
        created.append((issue["id"], num, issue["title"]))

    # Write issue number map for dependency comments
    id_to_num = {item[0]: item[1] for item in created}
    deps = {
        "S2": ["S1"], "S3": ["S2"], "S4": ["S1"],
        "S5": ["S3"], "S6": ["S5"], "S7": ["S2", "S4"],
        "S8": ["S6"], "S9": ["S3", "S6"], "S10": ["S4", "S7"],
        "S11": ["S5", "S6", "S7", "S8", "S9", "S10"],
        "S12": ["S11"], "S13": ["S12"],
        "S14": ["S13"], "S15": ["S14"], "S16": ["S15"],
    }
    for sid, upstream in deps.items():
        if sid not in id_to_num:
            continue
        refs = ", ".join(f"#{id_to_num[u]}" for u in upstream if u in id_to_num)
        if refs:
            gh(
                "issue", "comment", str(id_to_num[sid]),
                "--repo", REPO,
                "--body", f"**Dependencies:** {refs}",
            )

    print("\n=== Issue map ===")
    for sid, num, title in created:
        print(f"{sid}\t#{num}\t{title}")

    # Output JSON for project board script
    with open("/tmp/hecate_issues.json", "w") as f:
        json.dump([{"id": s, "number": n, "url": f"https://github.com/{REPO}/issues/{n}"} for s, n, _ in created], f, indent=2)


if __name__ == "__main__":
    main()
