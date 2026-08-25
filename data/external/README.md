# External matched-scaffold labels (SWE-bench Verified)

These files are **externally sourced** mini-SWE-agent pass/fail labels, not an
in-house Hecate inference run. They are a substitute for a new matched-scaffold
generation: Qwen3-Coder 480B/A35B Instruct vs Claude 4 Opus, both under
**mini-SWE-agent v1.0.0** on **2025-08-02**.

Do **not** merge this with in-house Qwen 2.5 7B / 72B SWE-bench **Lite** (300)
single-shot labels. This split is SWE-bench **Verified / bash-only (500)**.

| File | Role |
|------|------|
| `qwen3coder_vs_claude4opus_miniswe_external.csv` | Joined labels |
| `qwen3coder_vs_claude4opus_miniswe_external.json` | Same rows as JSON |
| `metadata.json` | Sources, scaffold versions, date pulled, caveats |

Schema: `instance_id, repo, small_model_resolved, large_model_resolved`.

Published rates (fail-closed): small **55.4%** (277/500), large **67.6%** (338/500).

Methods caveats (full text in `metadata.json`):

- Harness `swebench.yaml` at v1.0.0 sets `temperature=0.0`. Qwen3-Coder vendor recs are `temperature=0.7` / `top_p=0.8`; the published run's actual sampling is not in `metadata.yaml`.
- Seven Opus trajectories were git-peek flagged; two of those resolved. The primary file keeps all 500 so 67.6% still matches the leaderboard. Recoding those two successes as false is **67.2%**.

## Not a drop-in for router training

These are labels only. [`scripts/run_train.py`](../../scripts/run_train.py) still
needs SWE-bench Verified **issue-text prompts** joined onto these rows. Do not
use mini-SWE-agent trajectories as router input. Do not point Stage-4 v1
(`specs/015-router-training`) at this file; that spec is still the in-house Lite
path.

Regenerate with:

```bash
python scripts/extract_miniswe_labels.py --output-dir data/external
```
