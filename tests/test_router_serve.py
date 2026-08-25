"""Offline tests for experimental router serving (no HF / no GCS)."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from hecate.router.infer import (
    DEFAULT_THRESHOLD,
    EXPERIMENTAL_WARNING,
    logreg_params_from_payload,
    make_route_response,
    require_problem_statement,
    routing_decision,
    sigmoid_linear,
)


def test_sigmoid_linear_matches_known_values() -> None:
    assert sigmoid_linear([0.0, 0.0], [1.0, -1.0], 0.0) == pytest.approx(0.5)
    assert sigmoid_linear([10.0], [1.0], 0.0) == pytest.approx(1.0 / (1.0 + math.exp(-10.0)))
    assert 0.0 < sigmoid_linear([-8.0], [1.0], 0.0) < 0.5


def test_routing_decision_threshold() -> None:
    assert routing_decision(0.5, 0.5) == "small"
    assert routing_decision(0.49, 0.5) == "large"
    assert routing_decision(0.2, 0.1) == "small"


def test_make_route_response_always_warns() -> None:
    payload = make_route_response(0.61, run_id="run-abc", threshold=0.5)
    assert payload["p_small_resolves"] == pytest.approx(0.61)
    assert payload["routing_decision"] == "small"
    assert payload["model_version"] == "run-abc"
    assert payload["warning"] == EXPERIMENTAL_WARNING
    low = make_route_response(0.1, run_id="run-abc", threshold=DEFAULT_THRESHOLD)
    assert low["routing_decision"] == "large"
    assert low["warning"] == EXPERIMENTAL_WARNING


def test_require_problem_statement_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        require_problem_statement("  \n")
    assert require_problem_statement(" fix the bug ") == "fix the bug"


def test_fake_logreg_payload_scores_in_unit_interval() -> None:
    payload = {
        "kind": "logreg",
        "in_dim": 2,
        "hidden_size": 128,
        "dropout": 0.2,
        "state_dict": {"weight": [[1.0, 0.0]], "bias": [0.0]},
    }
    weight, bias = logreg_params_from_payload(payload)
    p = sigmoid_linear([4.0, 0.0], weight, bias)
    assert 0.0 <= p <= 1.0
    assert p > 0.9
    with pytest.raises(ValueError, match="logreg"):
        logreg_params_from_payload(
            {"kind": "mlp", "state_dict": {"weight": [[1.0]], "bias": [0.0]}}
        )


def test_from_checkpoint_roundtrip(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    from hecate.router.backends import FrozenHead
    from hecate.router.infer import load_head_payload

    head = FrozenHead("logreg", in_dim=3, epochs=1)
    module = head._build(torch)
    with torch.no_grad():
        module.weight.fill_(0.0)
        module.bias.fill_(0.0)
        module.weight[0, 0] = 2.0
    head._module = module
    head._device = torch.device("cpu")
    path = tmp_path / "head_logreg.pt"
    torch.save(head.state_dict(), path)
    loaded = FrozenHead.from_checkpoint(path)
    score = loaded.predict_proba([[1.0, 0.0, 0.0]])[0]
    assert 0.0 <= score <= 1.0
    assert score == pytest.approx(1.0 / (1.0 + math.exp(-2.0)))
    payload = load_head_payload(path)
    weight, bias = logreg_params_from_payload(payload)
    assert sigmoid_linear([1.0, 0.0, 0.0], weight, bias) == pytest.approx(score)


@pytest.mark.slow_router
def test_real_encoder_score_in_unit_interval() -> None:
    if os.getenv("RUN_ROUTER_INTEG") != "1":
        pytest.skip("set RUN_ROUTER_INTEG=1 to load ModernBERT + a real head")
    head_path = os.getenv("ROUTER_HEAD_PATH")
    if not head_path:
        pytest.skip("ROUTER_HEAD_PATH is required for the slow router test")
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from hecate.router.infer import load_scorer, read_manifest

    manifest_path = os.getenv("ROUTER_MANIFEST_PATH")
    if manifest_path is None:
        sibling = Path(head_path).with_name("manifest.json")
        manifest_path = str(sibling) if sibling.is_file() else None
    run_id = os.getenv("ROUTER_RUN_ID")
    if run_id is None and manifest_path:
        run_id = str(read_manifest(manifest_path).get("run_id") or "integ")
    scorer = load_scorer(
        head_path=head_path,
        manifest_path=manifest_path,
        run_id=run_id or "integ",
        device="cpu",
    )
    payload = scorer.route("Django queryset raises ValueError on empty filter.")
    assert 0.0 <= float(payload["p_small_resolves"]) <= 1.0
    assert payload["routing_decision"] in {"small", "large"}
    assert payload["warning"] == EXPERIMENTAL_WARNING
    assert payload["model_version"]
    json.dumps(payload)
