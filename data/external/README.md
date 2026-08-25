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
| `qwen3coder_vs_claude4opus_with_text.csv` | Labels plus Verified `problem_statement` / `base_commit` |
| `qwen3coder_vs_claude4opus_with_text.json` | Same rows as JSON |
| `metadata.json` | Sources, scaffold versions, date pulled, caveats |

Label schema: `instance_id, repo, small_model_resolved, large_model_resolved`.

Text schema: the four label columns plus `problem_statement, base_commit`. Gold
`patch` / `test_patch` are **not** stored.

Published rates (fail-closed): small **55.4%** (277/500), large **67.6%** (338/500).

Complementarity (fail-closed): both 258, Qwen-only 19, Opus-only 80, neither 143.
Oracle (either resolves) **71.4%**. Headroom vs always-Opus is **3.8pp**. Routing
value on this pair is **cost** (send the 258 both-win tasks to Qwen), not
accuracy lift over Opus.

Methods caveats (full text in `metadata.json`):

- Harness `swebench.yaml` at v1.0.0 sets `temperature=0.0`. Qwen3-Coder vendor recs are `temperature=0.7` / `top_p=0.8`; the published run's actual sampling is not in `metadata.yaml`.
- Seven Opus trajectories were git-peek flagged; two of those resolved. The primary file keeps all 500 so 67.6% still matches the leaderboard. Recoding those two successes as false is **67.2%**.

## Text-only trainer (v1)

[`scripts/run_train_text.py`](../../scripts/run_train_text.py) reads
`qwen3coder_vs_claude4opus_with_text.csv` (frozen ModernBERT, grouped-by-repo
CV). It is **not** [`scripts/run_train.py`](../../scripts/run_train.py) /
[`specs/015-router-training`](../../specs/015-router-training) (Lite
generations.jsonl). Do not use mini-SWE-agent trajectories as router input. Do
not merge with Qwen 2.5 Lite labels.

```bash
python scripts/run_train_text.py --backend frozen --config configs/router_text.yaml
```

Regenerate labels with:

```bash
python scripts/extract_miniswe_labels.py --output-dir data/external
```

Join Verified issue text with:

```bash
python scripts/join_miniswe_issue_text.py --output-dir data/external
```
