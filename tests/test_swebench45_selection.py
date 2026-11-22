import importlib.util
import json
from pathlib import Path

import pytest


def fixture():
    spec = importlib.util.spec_from_file_location("selection", "scripts/prepare_swebench45.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads(Path("configs/kimi_codex_swebench45_tasks.json").read_text())
    repos = [repo for repo, count in manifest["repo_counts"].items() for _ in range(count)]
    rows = [{"instance_id": iid, "repo": repo, "difficulty": "1-4 hours" if index < 42 else ">4 hours"}
            for index, (iid, repo) in enumerate(zip(manifest["instance_ids"], repos))]
    rows += [{"instance_id": f"excluded-{i}", "difficulty": "<15 min fix"} for i in range(455)]
    return module, manifest, rows


def test_selection_is_all_long_tasks_and_four_repeats():
    module, manifest, rows = fixture()
    result = module.select_tasks(list(reversed(rows)), manifest)
    assert [r["instance_id"] for r in result] == manifest["instance_ids"]
    assert len(result) == 45 and manifest["planned_attempts"] == 180
    assert len(manifest["repo_counts"]) == 8


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "label", "repo", "repetitions"])
def test_selection_rejects_changed_dataset_or_protocol(mutation):
    module, manifest, rows = fixture()
    if mutation == "missing": rows.pop()
    elif mutation == "duplicate": rows[-1] = rows[0]
    elif mutation == "label": rows[0]["difficulty"] = "15 min - 1 hour"
    elif mutation == "repo": rows[0]["repo"] = "other/repository"
    else: manifest["repetitions"] = 1
    with pytest.raises(ValueError):
        module.select_tasks(rows, manifest)
