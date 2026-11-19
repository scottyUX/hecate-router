"""TASK-004 causal ordering, missingness, split guards and adapter contracts."""

import copy
import json
from pathlib import Path
import pytest
import yaml
from hecate.telemetry.events import Event
from hecate.telemetry.collector import Collector, collect
from hecate.telemetry.state import FEATURES, StateBuilder
from hecate.telemetry.adapters import e7_session, mini


@pytest.fixture
def cfg():
    return yaml.safe_load(Path("configs/routing_observation.yaml").read_text())


def stream(extra=None):
    identity = {"task_id": "training-task", "split": "train"}
    events = []

    def add(kind, payload, t=None):
        n = len(events)
        events.append(
            Event(
                "ep",
                str(n),
                n,
                kind,
                "fixture",
                payload,
                t,
                "monotonic" if t is not None else None,
                identity=identity,
            )
        )

    add(
        "controller",
        {
            "episode_start": True,
            "active_model": "m1",
            "action_mask": [True, True],
            "request_limit": 40,
            "wall_limit_s": 2700,
            "context_limit": 16384,
        },
        0.0,
    )
    for i in range(5):
        add("model_request", {"request_id": str(i)}, float(i + 1))
        add(
            "model_response",
            {
                "request_id": str(i),
                "attempts": 2 if i == 0 else 1,
                "input_tokens": 100,
                "output_tokens": 10,
                "inference_s": 0.5,
            },
            float(i + 1),
        )
        add("tool_start", {"tool_id": str(i)})
        add(
            "tool_complete",
            {"tool_id": str(i), "command": True, "exit_code": 0, "timeout": False},
        )
    if extra:
        extra(add)
    add("boundary", {"verified": True}, 6.0)
    return events


def test_counts_masking_and_true_zero(cfg):
    rows = collect(stream(), cfg)
    assert len(rows) == 1
    f = rows[0]["features"]
    assert (
        f["completed_interactions"] == 5
        and f["model_requests"] == 5
        and f["transport_attempts"] == 6
    )
    assert f["command_failure_rate"] == 0 and f["repeated_errors"] == 0
    assert f["elapsed_s"] == 6 and f["input_tokens"] == 500
    state = StateBuilder(cfg).build(rows[0])
    assert not state["validity_mask"][FEATURES.index("advisor_progress")]
    assert state["validity_mask"][FEATURES.index("command_failure_rate")]


def test_duplicate_notifications_do_not_count_and_order_conflicts_fail(cfg):
    events = stream()
    duplicate = copy.deepcopy(events[-2].to_dict())
    duplicate["event_id"] = "duplicate"
    duplicate["sequence"] = events[-1].sequence
    tail = events[-1].to_dict()
    tail["sequence"] += 1
    rows = collect(
        events[:-1] + [Event.from_dict(duplicate), Event.from_dict(tail)], cfg
    )
    assert rows[0]["features"]["completed_interactions"] == 5
    c = Collector(cfg)
    c.push(events[0])
    assert c.push(events[0]) is None
    with pytest.raises(ValueError, match="ordering"):
        c.push(
            Event(
                "ep",
                "bad",
                0,
                "boundary",
                "test",
                {"verified": True},
                identity=events[0].identity,
            )
        )


def test_pending_parallel_tool_prevents_checkpoint(cfg):
    events = stream(lambda add: add("tool_start", {"tool_id": "pending"}))
    assert collect(events, cfg) == []
    collector = Collector(cfg)
    for event in events:
        collector.push(event)
    n = len(events)
    collector.push(
        Event(
            "ep",
            "finished",
            n,
            "tool_complete",
            "fixture",
            {"tool_id": "pending", "command": False},
            identity=events[0].identity,
        )
    )
    row = collector.push(
        Event(
            "ep",
            "safe",
            n + 1,
            "boundary",
            "fixture",
            {"verified": True},
            identity=events[0].identity,
        )
    )
    assert row["features"]["completed_interactions"] == 6


def test_later_evaluation_data_never_changes_prefix(cfg):
    events = stream()
    first = collect(events, cfg)
    term = Event(
        "ep",
        "end",
        len(events),
        "termination",
        "fixture",
        {"reason": "completed"},
        identity=events[0].identity,
    )
    assert collect(events + [term], cfg) == first
    with pytest.raises(ValueError, match="Evaluator"):
        Event("ep", "leak", 100, "controller", "fixture", {"resolved": True})


def test_missing_partial_usage_and_unknown_episode_start(cfg):
    events = stream()
    data = [e.to_dict() for e in events]
    data[0]["payload"].pop("episode_start")
    next(e for e in data if e["kind"] == "model_response")["payload"][
        "input_tokens"
    ] = None
    f = collect([Event.from_dict(e) for e in data], cfg)[0]["features"]
    assert f["input_tokens"] is None and f["elapsed_s"] is None
    assert f["output_tokens"] == 50


def test_normalization_train_only_frozen_hash_and_all_missing(cfg):
    rows = collect(stream(), cfg)
    builder = StateBuilder(cfg)
    split = {"training_ids": ["training-task"], "reserved_ids": ["held-out"]}
    normalizer = builder.fit(rows, split)
    state = StateBuilder(cfg, normalizer).build(rows[0], router_ready=True)
    assert all(x == 0 for x in state["vector"])
    assert state["mode"] == "router_ready"
    corrupted = copy.deepcopy(normalizer)
    corrupted["stats"]["input_tokens"]["mean"] = 42
    with pytest.raises(ValueError, match="hash"):
        StateBuilder(cfg, corrupted)
    reserved = copy.deepcopy(rows)
    reserved[0]["identity"]["task_id"] = "held-out"
    with pytest.raises(ValueError, match="training"):
        builder.fit(reserved, split)
    with pytest.raises(ValueError, match="Router-ready"):
        builder.build(rows[0], router_ready=True)


def test_visible_test_comparability_and_advisor_freshness(cfg):
    def extra(add):
        add(
            "visible_tests",
            {
                "selection_id": "suite",
                "conditions_id": "same",
                "parser_version": "v1",
                "tests": {"a": "failed", "b": "passed"},
            },
        )
        add(
            "visible_tests",
            {
                "selection_id": "suite",
                "conditions_id": "same",
                "parser_version": "v1",
                "tests": {"a": "passed", "b": "passed"},
            },
        )
        add(
            "advisor_assessment",
            {
                "validated": True,
                "schema": "hecate.assessment.v1",
                "progress": 0.5,
                "stuckness": 2.0,
            },
        )

    f = collect(stream(extra), cfg)[0]["features"]
    assert (
        f["visible_pass_delta"] == 1
        and f["advisor_progress"] == 0.5
        and f["advisor_stuckness"] is None
    )

    def different(add):
        extra(add)
        add(
            "visible_tests",
            {
                "selection_id": "other",
                "conditions_id": "same",
                "parser_version": "v1",
                "tests": {"a": "passed"},
            },
        )

    assert collect(stream(different), cfg)[0]["features"]["visible_pass_delta"] is None


def test_interleaved_episodes_are_separate_and_bad_clock_masked(cfg):
    events = stream()
    other = []
    for e in events:
        value = e.to_dict()
        value["episode_id"] = "other"
        other.append(Event.from_dict(value))
    interleaved = [x for pair in zip(events, other) for x in pair]
    assert len(collect(interleaved, cfg)) == 2
    data = [e.to_dict() for e in events]
    data[-1]["timestamp"] = -1
    assert (
        collect([Event.from_dict(e) for e in data], cfg)[0]["features"]["elapsed_s"]
        is None
    )


def test_legacy_e7_does_not_invent_tools(tmp_path, cfg):
    path = tmp_path / "legacy.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "step_completion",
                "step": 1,
                "total_agent_steps": 5,
                "terminated": True,
                "agent_actions": [],
            }
        )
        + "\n"
    )
    events, report = e7_session(path, episode_id="legacy", identity={}, config={})
    assert report["checkpoint_unverifiable"] and collect(events, cfg) == []
    assert not any(e.kind == "tool_complete" for e in events)


def test_mini_native_observation_only(tmp_path, cfg):
    rows = [
        {"request": 1, "messages": []},
        {
            "request": 2,
            "messages": [
                {"role": "assistant", "content": "```bash\nls\n```"},
                {
                    "role": "user",
                    "content": "<returncode>0</returncode>\n<output>file</output>",
                },
            ],
        },
    ]
    (tmp_path / "model.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    events, _ = mini(tmp_path, episode_id="mini", identity={}, config={})
    assert sum(e.kind == "tool_complete" for e in events) == 1
    assert not collect(events, cfg)  # only one completed interaction


def test_advisor_stale_after_window_and_missing_action_gate(cfg):
    events = stream()
    value = events[0].to_dict()
    value["payload"].pop("action_mask")
    events[0] = Event.from_dict(value)
    # Assessment before all five commands, then more than five completions.
    assessment = Event(
        "ep",
        "assessment",
        1,
        "advisor_assessment",
        "fixture",
        {"schema": "hecate.assessment.v1", "validated": True, "progress": 0.5},
        identity=events[0].identity,
    )
    data = [events[0], assessment]
    for event in events[1:-1]:
        row = event.to_dict()
        row["sequence"] += 1
        data.append(Event.from_dict(row))
    n = len(data)
    data.append(
        Event(
            "ep",
            "extra-start",
            n,
            "tool_start",
            "fixture",
            {"tool_id": "extra"},
            identity=events[0].identity,
        )
    )
    data.append(
        Event(
            "ep",
            "extra-done",
            n + 1,
            "tool_complete",
            "fixture",
            {"tool_id": "extra", "command": False},
            identity=events[0].identity,
        )
    )
    data.append(
        Event(
            "ep",
            "safe-final",
            n + 2,
            "boundary",
            "fixture",
            {"verified": True},
            identity=events[0].identity,
        )
    )
    rows = collect(data, cfg)
    assert rows[0]["features"]["advisor_progress"] is None
    norm = StateBuilder(cfg).fit(
        rows, {"training_ids": ["training-task"], "reserved_ids": []}
    )
    with pytest.raises(ValueError, match="controller"):
        StateBuilder(cfg, norm).build(rows[0], router_ready=True)


def test_bad_schema_and_identity_do_not_silently_convert(cfg):
    bad = copy.deepcopy(cfg)
    bad["features"] = list(reversed(bad["features"]))
    with pytest.raises(ValueError, match="schema"):
        StateBuilder(bad)
    events = stream()
    other = events[1].to_dict()
    other["identity"] = {"task_id": "wrong", "split": "train"}
    collector = Collector(cfg)
    collector.push(events[0])
    with pytest.raises(ValueError, match="identity"):
        collector.push(Event.from_dict(other))
