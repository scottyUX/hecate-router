# Quickstart: Router training v1

Offline (no weights):

```bash
python -m pytest tests/test_router.py -q
```

Live (after labels exist):

```bash
pip install -e ".[train]"
python scripts/run_train.py \
  --labels data/outputs/runs/exec-pilot-20/labels.jsonl \
  --generations data/outputs/runs/sweep-2x300-qwen/generations.jsonl \
  --output-dir data/outputs/runs/router-v1 \
  --run-id router-v1
```

`metrics.json` `mean_route_auc` > 0 is go; otherwise this is the v1 floor. Artifacts are gitignored.
