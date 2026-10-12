"""Offline tests for the r2 leaderboard-matched rerun (specs/018-three-model-r2)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # @dataclass resolves its module via sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = _load("run_three_model")
DRAW = _load("draw_three_model_subset")
R2 = RUN.EXPERIMENTS["r2"]


# --- task subset -----------------------------------------------------------


def test_subset_draw_is_deterministic_and_order_independent() -> None:
    tasks = [{"instance_id": f"r__r-{i}", "repo": "r/r", "difficulty": "x"} for i in range(100)]
    forward = DRAW.draw(tasks)
    assert forward == DRAW.draw(list(reversed(tasks)))
    assert len(forward) == DRAW.N_TASKS
    assert forward == sorted(forward, key=lambda t: t["instance_id"])


def test_committed_r2_tasks_are_the_seeded_subset_of_r1() -> None:
    r1 = json.loads((ROOT / RUN.EXPERIMENTS["r1"].tasks_file).read_text())
    r2 = json.loads((ROOT / R2.tasks_file).read_text())
    assert r2["tasks"] == DRAW.draw(r1["tasks"])
    assert r2["seed"] == DRAW.SEED
    assert len(r2["tasks"]) == r2["n"] == 50
    assert {t["instance_id"] for t in r2["tasks"]} <= {t["instance_id"] for t in r1["tasks"]}


# --- experiment presets ----------------------------------------------------


def test_r1_preset_is_unchanged() -> None:
    r1 = RUN.EXPERIMENTS["r1"]
    assert r1.models is RUN.MODELS
    assert r1.scaffold_version == "2.4.6"
    assert r1.config == Path("configs/miniswe_three_model.yaml")
    for spec in RUN.MODELS.values():
        assert spec.model_kwargs is None
        assert spec.agent_model == f"openrouter/{spec.slug}"
        overrides = RUN.config_overrides_for(spec, Path("cfg.yaml"))
        assert not any("reasoning" in o for o in overrides)


def test_r2_caps_sum_to_budget() -> None:
    assert sum(s.global_cost_limit_usd for s in R2.models.values()) == 130.0
    assert R2.scaffold_version == "2.0.0"


def test_r2_overrides_send_high_reasoning_and_no_temperature() -> None:
    for spec in R2.models.values():
        overrides = RUN.config_overrides_for(spec, Path("cfg.yaml"))
        kwargs = json.loads(next(o for o in overrides if o.startswith("model.model_kwargs=")).split("=", 1)[1])
        assert kwargs["reasoning"] == {"effort": "high"}
        assert kwargs["temperature"] is None
        assert spec.agent_model == spec.slug
        assert spec.model_class is not None


def test_r2_cache_control_only_for_opus_and_explicit() -> None:
    for key, spec in R2.models.items():
        overrides = RUN.config_overrides_for(spec, Path("cfg.yaml"))
        value = next(o for o in overrides if o.startswith("model.set_cache_control=")).split("=", 1)[1]
        assert json.loads(value) == ("default_end" if key == "opus" else None)


def test_r2_provider_routing_matches_leaderboard_providers() -> None:
    m = R2.models
    assert m["opus"].model_kwargs["provider"] == {"order": ["anthropic"], "allow_fallbacks": False}
    assert m["gemini"].model_kwargs["provider"] == {"order": ["google-ai-studio"], "allow_fallbacks": False}
    assert m["minimax"].model_kwargs["provider"] == {"only": ["novita", "minimax/fp8"]}
    mix = json.loads((ROOT / RUN.LEADERBOARD_REFERENCE_DIR / "minimax_provider_mix.json").read_text())
    assert {"Novita", "Minimax"} <= set(mix["calls"])


def test_version_guard_refuses_wrong_install(monkeypatch, capsys) -> None:
    monkeypatch.setattr(RUN, "_miniswe_version", lambda: "2.4.6")
    assert RUN.main(["--experiment", "r2", "--model", "gemini"]) == 1
    assert "runs on mini-swe-agent 2.0.0, installed is 2.4.6" in capsys.readouterr().err


# --- config vs leaderboard (needs the agent extra) -------------------------


def test_leaderboard_config_is_builtin_swebench_yaml() -> None:
    config = pytest.importorskip("minisweagent.config")
    builtin = yaml.safe_load((Path(config.__file__).parent / "benchmarks/swebench.yaml").read_text())
    ours = yaml.safe_load((ROOT / R2.config).read_text())
    assert ours["agent"] == builtin["agent"]
    assert ours["environment"] == {**builtin["environment"], "pull_timeout": 300}
    for key in ("observation_template", "format_error_template"):
        assert ours["model"][key] == builtin["model"][key]
    assert ours["model"]["model_kwargs"] == {**builtin["model"]["model_kwargs"], "temperature": None}


def test_config_check_passes_r2_and_fails_r1() -> None:
    pytest.importorskip("minisweagent")
    check = _load("check_leaderboard_config")
    assert check.check("r2") == 0
    assert check.check("r1") == 1


def test_headers_model_sends_extra_headers_as_http_headers(monkeypatch) -> None:
    pytest.importorskip("minisweagent")
    from hecate.agent import openrouter_headers

    sent = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"ok": True}

    def fake_post(url, headers, data, timeout):
        sent.update(headers=headers, body=json.loads(data))
        return _Resp()

    monkeypatch.setattr(openrouter_headers.requests, "post", fake_post)
    model = openrouter_headers.OpenRouterHeadersModel(
        model_name="anthropic/claude-opus-4.5",
        model_kwargs=R2.models["opus"].model_kwargs,
    )
    model._query([{"role": "user", "content": "hi"}])
    assert sent["headers"]["anthropic-beta"] == "interleaved-thinking-2025-05-14"
    assert "extra_headers" not in sent["body"]
    assert sent["body"]["reasoning"] == {"effort": "high"}
    # The config, and so the trajectory, still records the header.
    assert model.config.model_kwargs["extra_headers"]
