"""Offline tests for S11 generation runner orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from git import Repo as GitRepo

from hecate.caching import cache_key, decoding_fingerprint
from hecate.cost import BudgetConfig, CostTracker, ModelPricing
from hecate.data import SwebenchTask, read_jsonl
from hecate.generation.client import CompletionResult
from hecate.generation.runner import load_run_config, run_generation
from hecate.scaffold import PROMPT_VERSION, build_context, prompt_hash, render_prompt

VALID_PATCH = """\
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,2 +1,2 @@
 def base():
-    return 1
+    return 2
"""

_SYNTHETIC_GOLD = """\
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,2 +1,2 @@
 def base():
-    return 1
+    return 2
--- /dev/null
+++ b/pkg/new_mod.py
@@ -0,0 +1,2 @@
+def added():
+    return 3
"""

QWEN_7B = "qwen/qwen-2.5-7b-instruct"


def _make_local_task(tmp_path: Path) -> tuple[SwebenchTask, Path]:
    work_dir = tmp_path / "work"
    work_repo = GitRepo.init(work_dir)
    (work_dir / "pkg").mkdir()
    (work_dir / "pkg" / "mod.py").write_text("def base():\n    return 1\n")
    work_repo.index.add(["pkg/mod.py"])
    base_commit = work_repo.index.commit("base").hexsha

    cache_dir = tmp_path / "repo_cache"
    cache_dir.mkdir()
    GitRepo.clone_from(str(work_dir), str(cache_dir / "acme__widget.git"), bare=True)

    task = SwebenchTask(
        instance_id="acme__widget-1",
        repo="acme/widget",
        base_commit=base_commit,
        problem_statement="widget is broken",
        patch=_SYNTHETIC_GOLD,
    )
    return task, cache_dir


class _CountingCompleter:
    def __init__(self, text: str = VALID_PATCH) -> None:
        self.calls = 0
        self.text = text

    async def complete(
        self,
        *,
        model_slug: str,
        prompt: str,
        decoding: dict[str, Any] | None = None,
    ) -> CompletionResult:
        self.calls += 1
        return CompletionResult(
            model_slug=model_slug,
            text=self.text,
            prompt_tokens=100,
            completion_tokens=50,
            decoding_params=dict(decoding or {}),
        )


@pytest.mark.asyncio
async def test_mocked_complete_writes_record(tmp_path: Path) -> None:
    task, repo_cache = _make_local_task(tmp_path)
    completer = _CountingCompleter()
    config = load_run_config(
        tasks=1,
        model=QWEN_7B,
        dry_run=False,
        output_dir=tmp_path / "out",
        cache_dir=tmp_path / "gen_cache",
        ledger_path=tmp_path / "ledger.json",
        run_id="test1",
        repo_cache_dir=repo_cache,
    )
    result = await run_generation(config, tasks=[task], completer=completer)

    assert completer.calls == 1
    assert result.pairs_attempted == 1
    assert result.pairs_generated == 1
    assert result.pairs_cache_hit == 0
    records = read_jsonl(result.records_path)
    assert len(records) == 1
    assert records[0].patch_parse_ok is True
    assert records[0].extracted_patch is not None
    assert records[0].cost_usd is not None and records[0].cost_usd > 0
    assert result.manifest_path.is_file()


@pytest.mark.asyncio
async def test_cache_hit_skips_provider(tmp_path: Path) -> None:
    task, repo_cache = _make_local_task(tmp_path)
    completer = _CountingCompleter()
    shared = dict(
        tasks=1,
        model=QWEN_7B,
        dry_run=False,
        cache_dir=tmp_path / "gen_cache",
        ledger_path=tmp_path / "ledger.json",
        repo_cache_dir=repo_cache,
    )
    first = load_run_config(output_dir=tmp_path / "out1", run_id="r1", **shared)
    await run_generation(first, tasks=[task], completer=completer)
    assert completer.calls == 1

    second = load_run_config(output_dir=tmp_path / "out2", run_id="r2", **shared)
    result = await run_generation(second, tasks=[task], completer=completer)
    assert completer.calls == 1  # no new call
    assert result.pairs_cache_hit == 1
    assert result.pairs_generated == 1


@pytest.mark.asyncio
async def test_budget_refuse_skips_provider(tmp_path: Path) -> None:
    task, repo_cache = _make_local_task(tmp_path)
    completer = _CountingCompleter()
    ledger = tmp_path / "ledger.json"
    # Seed ledger near ceiling so upper-bound authorize fails.
    tracker = CostTracker(
        ledger_path=ledger,
        budget=BudgetConfig(target_usd=38.0, ceiling_usd=100.0),
        pricing={
            QWEN_7B: ModelPricing(
                slug=QWEN_7B, input_cost_per_1m=0.04, output_cost_per_1m=0.10
            )
        },
    )
    tracker.record(99.9999)

    config = load_run_config(
        tasks=1,
        model=QWEN_7B,
        dry_run=False,
        output_dir=tmp_path / "out",
        cache_dir=tmp_path / "gen_cache",
        ledger_path=ledger,
        run_id="budget",
        repo_cache_dir=repo_cache,
    )
    result = await run_generation(config, tasks=[task], completer=completer)
    assert completer.calls == 0
    assert result.pairs_refused_budget == 1
    records = read_jsonl(result.records_path)
    assert records[0].raw_response is None


@pytest.mark.asyncio
async def test_manifest_has_required_fields(tmp_path: Path) -> None:
    task, repo_cache = _make_local_task(tmp_path)
    config = load_run_config(
        tasks=1,
        model=QWEN_7B,
        dry_run=True,
        output_dir=tmp_path / "out",
        cache_dir=tmp_path / "gen_cache",
        ledger_path=tmp_path / "ledger.json",
        run_id="manifest",
        repo_cache_dir=repo_cache,
    )
    result = await run_generation(config, tasks=[task])
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    for key in (
        "run_id",
        "timestamp",
        "git_commit",
        "config_snapshot",
        "model_slugs",
        "total_cost_usd",
    ):
        assert key in payload
    assert payload["dry_run"] is True
    assert payload["model_slugs"] == [QWEN_7B]


@pytest.mark.asyncio
async def test_shared_scaffold_prompt_hash(tmp_path: Path) -> None:
    task, repo_cache = _make_local_task(tmp_path)
    context = build_context(
        task.instance_id, method="oracle", task=task, cache_dir=repo_cache
    )
    prompt = render_prompt(task, context)
    h1 = prompt_hash(prompt)
    h2 = prompt_hash(render_prompt(task, context))
    assert h1 == h2
    # Cache key differs only by model slug when prompt is shared.
    dec_fp = decoding_fingerprint({"temperature": 0.0, "max_tokens": 4096})
    k_a = cache_key(task.instance_id, QWEN_7B, h1, PROMPT_VERSION, dec_fp)
    k_b = cache_key(
        task.instance_id,
        "meta-llama/llama-3.1-8b-instruct",
        h1,
        PROMPT_VERSION,
        dec_fp,
    )
    assert k_a != k_b


def test_load_run_config_rejects_unknown_slug() -> None:
    with pytest.raises(ValueError, match="Unknown model slug"):
        load_run_config(tasks=1, model="not/a-real-model")


def test_dry_run_cli_exits_zero(tmp_path: Path) -> None:
    """Pilot CLI dry-run with injected paths via library (no network)."""
    task, repo_cache = _make_local_task(tmp_path)

    async def _run() -> None:
        config = load_run_config(
            tasks=1,
            model=QWEN_7B,
            dry_run=True,
            output_dir=tmp_path / "cli-out",
            cache_dir=tmp_path / "gen_cache",
            ledger_path=tmp_path / "ledger.json",
            repo_cache_dir=repo_cache,
        )
        result = await run_generation(config, tasks=[task])
        assert result.pairs_attempted == 1
        assert result.manifest_path.is_file()

    import asyncio

    asyncio.run(_run())
