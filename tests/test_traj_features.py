"""Offline tests for trajectory feature extraction (hecate.agent.traj_features)."""

from __future__ import annotations

import pytest

from hecate.agent.traj_features import _classify, _edit_targets, extract

PATCH = (
    "diff --git a/pkg/core.py b/pkg/core.py\n"
    "--- a/pkg/core.py\n+++ b/pkg/core.py\n"
    "@@ -1,2 +1,2 @@\n-    return a - b\n+    return a + b\n"
)


def _traj(steps: list[list[tuple[str, str, int]]]) -> dict:
    """Build a mini-SWE v2 trajectory: each step is [(command, output, rc), ...]."""
    messages: list[dict] = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "task"},
    ]
    t = 1000.0
    n = 0
    for i, step in enumerate(steps):
        t += 10
        actions = []
        results = []
        for cmd, out, rc in step:
            n += 1
            actions.append({"command": cmd, "tool_call_id": f"c{n}"})
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": f"c{n}",
                    "content": out,
                    "extra": {"raw_output": out, "returncode": rc, "timestamp": t + 1},
                }
            )
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "extra": {
                    "actions": actions,
                    "timestamp": t,
                    "response": {
                        "provider": "Anthropic",
                        "usage": {
                            "prompt_tokens": 1000 * (i + 1),
                            "completion_tokens": 50,
                            "cost": 0.01,
                            "prompt_tokens_details": {"cached_tokens": 900 * i},
                        },
                    },
                },
            }
        )
        messages.extend(results)
    messages.append({"role": "exit", "content": PATCH})
    return {
        "instance_id": "pkg__pkg-1",
        "info": {
            "exit_status": "Submitted",
            "submission": PATCH,
            "model_stats": {"instance_cost": 0.04, "api_calls": len(steps)},
        },
        "messages": messages,
    }


TRAJ = _traj(
    [
        [("grep -rn 'def add' pkg/", "pkg/core.py:1:def add", 0), ("cat pkg/core.py", "...", 0)],
        [("cat > reproduce.py <<'EOF'\nfrom pkg.core import add\nassert add(1, 2) == 3\nEOF\npython reproduce.py",
          "Traceback (most recent call last):\nAssertionError", 1)],
        [("sed -i 's/a - b/a + b/' pkg/core.py", "", 0)],
        [("python reproduce.py", "", 0)],
        [("python -m pytest tests/test_core.py -q 2>&1 | tail -3", "===== 1 failed, 3 passed in 0.1s =====", 0)],
        [("sed -i 's/x/y/' pkg/core.py", "", 0)],
        [("python -m pytest tests/test_core.py -q", "===== 4 passed in 0.1s =====", 0)],
        [("git diff -- pkg/core.py > patch.txt", "", 0)],
        [("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt", PATCH, 0)],
    ]
)


@pytest.mark.parametrize(
    "command, kinds",
    [
        ("sed -n 1,40p pkg/core.py", {"inspect"}),
        ("sed -i 's/a/b/' pkg/core.py", {"edit"}),
        ("cat > pkg/core.py <<'EOF'\nif a > b:\n    python = 1\nEOF", {"edit"}),
        ('python -c "print(1 > 0)"', {"script"}),
        ("python3 - <<EOF\nprint(1)\nEOF", {"script"}),
        ("python tests/runtests.py queries 2>&1 | tail -20", {"test"}),
        ("cd /testbed && python -m pytest a.py -x", {"test"}),
        ("grep -rn foo pkg/ | head", {"inspect", "search"}),
        ("git checkout -- pkg/core.py", {"revert"}),
        ("python reproduce.py > /dev/null 2>&1", {"script"}),
        ("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt", {"submit"}),
    ],
)
def test_classify(command: str, kinds: set[str]) -> None:
    assert _classify(command) == kinds


def test_heredoc_body_is_not_shell() -> None:
    cmd = "cat > t.py <<'EOF'\nx = 1 > 0\nopen_file = 2\nEOF\npython t.py"
    assert _classify(cmd) == {"edit", "script"}
    assert _edit_targets(cmd) == {"t.py"}


def test_extract_counts() -> None:
    f = extract(TRAJ, model="opus")
    assert f.steps == 9 and f.actions == 10 and f.api_calls == 9
    assert f.submitted and f.exit_status == "Submitted"
    # source edits only: the repro heredoc and patch.txt are scratch writes
    assert f.edit_actions == 2
    assert f.test_runs == 2 and f.test_runs_failed == 1 and f.test_runs_passed == 1
    # pytest summary beats the masked return code of `| tail`
    assert f.script_runs == 2 and f.script_runs_failed == 1
    assert f.failed_run_then_edit == 2
    assert f.edit_run_cycles == 2
    assert f.tracebacks == 1 and f.nonzero_returncodes == 1
    assert f.first_edit_step == 3 and f.first_test_step == 5
    assert f.last_run_before_submit == "pass"
    assert f.patch_files == 1 and f.patch_lines_added == 1 and f.patch_lines_removed == 1
    assert f.files_written == 3  # pkg/core.py, reproduce.py, patch.txt
    assert f.helper_files_written == 2
    assert f.files_inspected == 1  # pkg/core.py
    assert f.openrouter_cost_usd == pytest.approx(0.09)
    assert f.max_prompt_tokens == 9000 and f.cached_tokens == 900 * sum(range(9))
    assert f.providers == "Anthropic"
    assert f.runtime_s == pytest.approx(81.0)
    assert f.time_to_first_test_s == pytest.approx(41.0)
    assert f.time_to_submit_s == pytest.approx(81.0)


def test_extract_handles_empty_trajectory() -> None:
    f = extract({"instance_id": "x", "info": {}, "messages": []}, model="m")
    assert f.steps == 0 and f.actions == 0 and not f.submitted
    assert f.runtime_s is None and f.last_run_before_submit is None
