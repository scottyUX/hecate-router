from __future__ import annotations

import pytest

from hecate.utils.run_ids import RunIdError, make_run_id, parse_run_id


def test_make_and_parse_roundtrip() -> None:
    rid = make_run_id(exp=2, arm="k1", split="leave-repo", seed=0)
    assert rid == "exp-02_arm-k1_split-leaverepo_seed-0"
    parsed = parse_run_id(rid)
    assert parsed["exp"] == "02"
    assert parsed["arm"] == "k1"
    assert parsed["split"] == "leaverepo"
    assert parsed["seed"] == "0"


def test_rerun_suffix_and_rejects() -> None:
    rid = make_run_id(exp=1, arm="k0", split="specialist", seed=0, run=2)
    assert rid.endswith("_run-2")
    with pytest.raises(RunIdError):
        make_run_id(exp=2, arm="k1", split="x", seed=0, run=1)
    with pytest.raises(RunIdError, match="missing"):
        parse_run_id("exp-02_arm-k1")
    with pytest.raises(RunIdError, match="refusing"):
        parse_run_id("e2/armD")
