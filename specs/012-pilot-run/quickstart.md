# Quickstart: Pilot Run

```bash
pip install -e ".[dev]"
# OPENROUTER_API_KEY in .env

python scripts/run_pilot.py \
  --tasks 20 \
  --model qwen/qwen-2.5-7b-instruct \
  --output-dir data/outputs/runs/pilot-20x1
```

Inspect:

```bash
wc -l data/outputs/runs/pilot-20x1/generations.jsonl
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('data/outputs/runs/pilot-20x1/manifest.json').read_text())
print({k: m[k] for k in ('total_cost_usd','cost_per_sample_usd','wall_clock_s','pairs_attempted','pairs_generated')})
PY
```
