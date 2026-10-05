"""Derive per-run behavioral features from mini-SWE-agent trajectories.

One row per (model, instance) ``.traj.json``. Everything here is read off the
trajectory alone, with no grading involved, so the features can be joined to
``resolved`` later by ``instance_id`` without leaking the label into them.

Command classification is heuristic (bash-only agent: an edit is ``sed -i``, a
heredoc redirect, a Python ``open(..., "w")``, ...). Where an exact answer
exists it is used instead: files the agent actually changed come from the
submitted patch, not from guessing at edit commands.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

SUBMIT_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"

# Runs of the repository's own test suite (vs. ad-hoc scripts the agent wrote).
_TEST_SUITE = re.compile(
    r"(\bpytest\b|-m\s+pytest|runtests\.py|-m\s+unittest|\bbin/test\b|"
    r"manage\.py\s+test|\btox\b|sympy\.testing|\bsympy\.test\(|setup\.py\s+test)"
)
# python <file>.py, python -c, python heredoc: agent-written verification.
_SCRIPT_RUN = re.compile(r"(^|[\s;&|(])(\S*/)?python[\d.]*\s+(?!-m\s)(-c\b|-?\s*<<|[^\s|;&<>-]\S*\.py\b)")
_REVERT = re.compile(
    r"(\bgit\s+(checkout|restore)\s+(--\s+)?\S|\bgit\s+stash\b|"
    r"\bcp\s+\S+\.(bak|orig)\s|\bmv\s+\S+\.(bak|orig)\s)"
)
_INSPECT = re.compile(r"(^|[;&(]|&&)\s*(cd\s+\S+\s*&&\s*)?(cat|head|tail|nl|less|more|sed\s+-n|awk|grep|rg)\b", re.M)
_SEARCH = re.compile(r"(^|[;&(]|&&)\s*(cd\s+\S+\s*&&\s*)?(grep\s+(-\w+\s+)*-\w*[rR]|rg\b|find\b|ls\b|git\s+grep|tree\b)", re.M)
_PATH = re.compile(
    r"(?<![\w.])(?:/testbed/|\./)?((?:[\w.-]+/)*[\w.-]+\.(?:py|pyi|pyx|c|h|cfg|toml|ini|rst|txt|md|json|ya?ml|js|html|css))\b"
)
# Helper files the agent writes for itself (repro scripts, fix scripts, the
# patch.txt the submission protocol asks for): root-level files with these
# stems, or anything under /tmp.
_SCRATCH_FILE = re.compile(
    r"^/tmp/|^(?!.*/)(patch|fix|apply|repro|reproduce|reproduction|test|debug|check|verify|output|tmp|temp|scratch)[\w.-]*$"
)

# Output-based test verdicts; return codes lie when output is piped (| tail).
_DJANGO_OK = re.compile(r"^Ran \d+ tests? in [\d.]+s\s*\n+\s*OK\b", re.M)
_DJANGO_FAIL = re.compile(r"^FAILED \((failures|errors)=", re.M)
_PYTEST_SUMMARY = re.compile(r"=+ .*?\b(\d+ (passed|failed|error|errors))\b.* =+")
_PYTEST_FAIL = re.compile(r"\b\d+ (failed|errors?)\b")
_TRACEBACK = re.compile(r"^Traceback \(most recent call last\):", re.M)
_TIMEOUT = re.compile(r"timed out|TimeoutExpired", re.I)


@dataclass
class Action:
    step: int  # 1-based index of the assistant turn that issued it
    command: str
    output: str
    returncode: int | None
    timestamp: float | None
    exception: str | None
    kinds: set[str] = field(default_factory=set)
    test_outcome: str | None = None  # pass / fail / unknown, for test + script runs


@dataclass
class TrajFeatures:
    model: str
    instance_id: str
    exit_status: str | None
    submitted: bool
    # scale
    steps: int
    api_calls: int | None
    actions: int
    actions_per_step: float
    format_errors: int
    # cost / tokens
    cost_usd: float | None
    openrouter_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cached_tokens: int
    max_prompt_tokens: int
    providers: str
    # what it did
    inspect_actions: int
    search_actions: int
    edit_actions: int
    revert_actions: int
    test_runs: int
    test_runs_passed: int
    test_runs_failed: int
    script_runs: int
    script_runs_passed: int
    script_runs_failed: int
    files_inspected: int
    files_written: int  # every write target, incl. helper scripts
    helper_files_written: int  # write targets not in the final patch
    # errors
    nonzero_returncodes: int
    tracebacks: int
    timeouts: int
    # dynamics
    edit_run_cycles: int
    failed_run_then_edit: int
    first_edit_step: int | None
    first_test_step: int | None
    first_run_step: int | None
    first_edit_frac: float | None
    first_test_frac: float | None
    last_run_before_submit: str | None
    runtime_s: float | None
    time_to_first_test_s: float | None
    time_to_first_edit_s: float | None
    time_to_submit_s: float | None
    # final patch (ground truth for "files modified")
    patch_chars: int
    patch_files: int
    patch_lines_added: int
    patch_lines_removed: int
    patch_touches_tests: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_commands(command: str) -> list[str]:
    """Top-level segments of a shell command (best effort, never raises)."""
    return [s for s in re.split(r"\s*(?:&&|\|\||;|\n)\s*", command) if s.strip()]


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")


def _strip_heredocs(command: str) -> str:
    """Drop heredoc bodies, keeping the opening line and anything after EOF."""
    out: list[str] = []
    terminator: str | None = None
    for line in command.splitlines():
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        out.append(line)
        m = _HEREDOC.search(line)
        if m:
            terminator = m.group(2)
    return "\n".join(out)


def _shell_part(command: str) -> str:
    """The shell syntax of a command, minus heredoc bodies and quoted strings.

    Redirects, edit verbs and interpreter calls are only meaningful here: a
    ``>`` or ``python`` inside a heredoc body or a ``python -c "..."`` string
    is file content, not shell.
    """
    shell = _strip_heredocs(command)
    shell = re.sub(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"", "''", shell)
    return re.sub(r"\d?>&\d|\d?>\s*/dev/null", " ", shell)


_EDIT_VERB = re.compile(
    r"(\bsed\s+(-\w+\s+)*-i|\bsed\s+-i|\bperl\s+(-\w+\s+)*-p?i|\bed\s+-s|"
    r"\btee\s+(-a\s+)?[\w./-]+|\bgit\s+apply\b|\bpatch\s+-p|"
    r"\b(cp|mv)\s+\S+\.(bak|orig)\s)"
)
_REDIRECT = re.compile(r"(?<![<>&\d])>{1,2}\s*((?:/testbed/)?[\w./-]+)")
_PY_WRITE = re.compile(
    r"open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][wa]|Path\(\s*['\"]([^'\"]+)['\"]\s*\)\.write_text"
)


def _classify(command: str) -> set[str]:
    if SUBMIT_MARKER in command:
        return {"submit"}
    shell = _shell_part(command)
    kinds: set[str] = set()
    if _TEST_SUITE.search(shell):
        kinds.add("test")
    elif _SCRIPT_RUN.search(shell):
        kinds.add("script")
    if _REVERT.search(shell):
        kinds.add("revert")
    if _EDIT_VERB.search(shell) or _REDIRECT.search(shell) or _PY_WRITE.search(command):
        kinds.add("edit")
    if _SEARCH.search(shell):
        kinds.add("search")
    if _INSPECT.search(shell) and "edit" not in kinds:
        kinds.add("inspect")
    if re.search(r"\bgit\s+(diff|status|log|show)\b", shell):
        kinds.add("vcs")
    return kinds


def _norm(path: str) -> str:
    return path.removeprefix("/testbed/").removeprefix("./")


def _edit_targets(command: str) -> set[str]:
    shell = _shell_part(command)
    targets = {_norm(m.group(1)) for m in _REDIRECT.finditer(shell)}
    for m in _PY_WRITE.finditer(command):
        targets.add(_norm(m.group(1) or m.group(2)))
    for seg in _split_commands(shell):
        if re.match(r"\s*(sed|perl|tee)\b", seg):
            targets |= {_norm(m.group(0)) for m in _PATH.finditer(seg)}
    return {t for t in targets if t and t != "/dev/null"}


def _paths(command: str) -> set[str]:
    return {_norm(m.group(0)) for m in _PATH.finditer(_strip_heredocs(command))}


def _test_outcome(output: str, returncode: int | None) -> str:
    if _DJANGO_FAIL.search(output) or (
        _PYTEST_SUMMARY.search(output) and _PYTEST_FAIL.search(output)
    ):
        return "fail"
    if _DJANGO_OK.search(output) or _PYTEST_SUMMARY.search(output):
        return "pass"
    if _TRACEBACK.search(output) or (returncode not in (None, 0)):
        return "fail"
    if returncode == 0:
        return "pass"
    return "unknown"


def _patch_stats(patch: str) -> tuple[int, int, int, bool]:
    files = re.findall(r"^diff --git a/(\S+) b/", patch, re.M)
    added = sum(1 for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in patch.splitlines() if l.startswith("-") and not l.startswith("---"))
    touches_tests = any(re.search(r"(^|/)(tests?|testing)(/|_)|test_\w+\.py$", f) for f in files)
    return len(set(files)), added, removed, touches_tests


def parse_actions(messages: list[dict[str, Any]]) -> list[Action]:
    """Pair each issued command with its tool result, in order."""
    results = {
        m.get("tool_call_id"): m for m in messages if m.get("role") == "tool"
    }
    actions: list[Action] = []
    step = 0
    for m in messages:
        if m.get("role") != "assistant":
            continue
        step += 1
        extra = m.get("extra") or {}
        for a in extra.get("actions") or []:
            res = results.get(a.get("tool_call_id")) or {}
            rextra = res.get("extra") or {}
            cmd = a.get("command") or ""
            act = Action(
                step=step,
                command=cmd,
                output=str(rextra.get("raw_output") or res.get("content") or ""),
                returncode=rextra.get("returncode"),
                timestamp=rextra.get("timestamp") or extra.get("timestamp"),
                exception=rextra.get("exception_info") or None,
                kinds=_classify(cmd),
            )
            if "edit" in act.kinds:
                targets = _edit_targets(cmd)
                if targets and all(_SCRATCH_FILE.search(t) for t in targets):
                    # Writing a repro script or patch.txt is not a source edit.
                    act.kinds = (act.kinds - {"edit"}) | {"scratch"}
            if act.kinds & {"test", "script"}:
                act.test_outcome = _test_outcome(act.output, act.returncode)
            actions.append(act)
    return actions


def extract(traj: dict[str, Any], *, model: str, patch: str | None = None) -> TrajFeatures:
    info = traj.get("info") or {}
    messages = traj.get("messages") or []
    stats = info.get("model_stats") or {}
    actions = parse_actions(messages)
    steps = sum(1 for m in messages if m.get("role") == "assistant")
    if patch is None:
        patch = str(info.get("submission") or "")

    usage_rows = [
        ((m.get("extra") or {}).get("response") or {})
        for m in messages
        if m.get("role") == "assistant"
    ]
    usages = [r.get("usage") or {} for r in usage_rows]
    prompt = [u.get("prompt_tokens") or 0 for u in usages]

    def _tok(u: dict, *path: str) -> int:
        cur: Any = u
        for p in path:
            cur = (cur or {}).get(p) if isinstance(cur, dict) else None
        return int(cur or 0)

    ts = [
        t
        for m in messages
        for t in [(m.get("extra") or {}).get("timestamp")]
        if isinstance(t, (int, float))
    ]
    t0 = min(ts) if ts else None

    def first(kind: str) -> Action | None:
        return next((a for a in actions if kind in a.kinds), None)

    def since(a: Action | None) -> float | None:
        return round(a.timestamp - t0, 2) if a and a.timestamp and t0 else None

    runs = [a for a in actions if a.kinds & {"test", "script"}]
    tests = [a for a in runs if "test" in a.kinds]
    scripts = [a for a in runs if "script" in a.kinds]

    # Collapse to a coarse phase sequence to count edit -> run iterations.
    phases: list[str] = []
    for a in actions:
        p = "edit" if "edit" in a.kinds else "run" if a.kinds & {"test", "script"} else None
        if p and (not phases or phases[-1] != p):
            phases.append(p)
    edit_run_cycles = sum(1 for x, y in zip(phases, phases[1:]) if (x, y) == ("edit", "run"))

    failed_then_edit = 0
    pending_fail = False
    for a in actions:
        if a.kinds & {"test", "script"}:
            pending_fail = a.test_outcome == "fail"
        elif "edit" in a.kinds and pending_fail:
            failed_then_edit += 1
            pending_fail = False

    submit = first("submit")
    pre_submit_runs = [a for a in runs if not submit or a.step <= submit.step]

    written: set[str] = set()
    inspected: set[str] = set()
    for a in actions:
        if a.kinds & {"edit", "scratch"}:
            written |= _edit_targets(a.command)
        if a.kinds & {"inspect", "search"} and "edit" not in a.kinds:
            inspected |= {p for p in _paths(a.command) if not _SCRATCH_FILE.search(p)}

    p_files, p_add, p_rm, p_tests = _patch_stats(patch)
    patch_paths = set(re.findall(r"^diff --git a/(\S+) b/", patch, re.M))
    first_edit, first_test = first("edit"), first("test")
    first_run = runs[0] if runs else None

    return TrajFeatures(
        model=model,
        instance_id=str(traj.get("instance_id") or ""),
        exit_status=info.get("exit_status"),
        submitted=bool(patch.strip()),
        steps=steps,
        api_calls=stats.get("api_calls"),
        actions=len(actions),
        actions_per_step=round(len(actions) / steps, 3) if steps else 0.0,
        format_errors=sum(
            1
            for m in messages[2:]
            if m.get("role") == "user" and "Tool call error" in str(m.get("content"))
        ),
        cost_usd=stats.get("instance_cost"),
        openrouter_cost_usd=round(sum(float(u.get("cost") or 0) for u in usages), 6),
        prompt_tokens=sum(prompt),
        completion_tokens=sum(_tok(u, "completion_tokens") for u in usages),
        reasoning_tokens=sum(_tok(u, "completion_tokens_details", "reasoning_tokens") for u in usages),
        cached_tokens=sum(_tok(u, "prompt_tokens_details", "cached_tokens") for u in usages),
        max_prompt_tokens=max(prompt, default=0),
        providers=",".join(sorted({str(r["provider"]) for r in usage_rows if r.get("provider")})),
        inspect_actions=sum(1 for a in actions if "inspect" in a.kinds),
        search_actions=sum(1 for a in actions if "search" in a.kinds),
        edit_actions=sum(1 for a in actions if "edit" in a.kinds),
        revert_actions=sum(1 for a in actions if "revert" in a.kinds),
        test_runs=len(tests),
        test_runs_passed=sum(1 for a in tests if a.test_outcome == "pass"),
        test_runs_failed=sum(1 for a in tests if a.test_outcome == "fail"),
        script_runs=len(scripts),
        script_runs_passed=sum(1 for a in scripts if a.test_outcome == "pass"),
        script_runs_failed=sum(1 for a in scripts if a.test_outcome == "fail"),
        files_inspected=len(inspected),
        files_written=len(written),
        helper_files_written=len(written - patch_paths),
        nonzero_returncodes=sum(
            1 for a in actions if a.returncode not in (None, 0) and "submit" not in a.kinds
        ),
        tracebacks=sum(1 for a in actions if _TRACEBACK.search(a.output)),
        timeouts=sum(1 for a in actions if a.exception or (a.returncode == -1 and _TIMEOUT.search(a.output))),
        edit_run_cycles=edit_run_cycles,
        failed_run_then_edit=failed_then_edit,
        first_edit_step=first_edit.step if first_edit else None,
        first_test_step=first_test.step if first_test else None,
        first_run_step=first_run.step if first_run else None,
        first_edit_frac=round(first_edit.step / steps, 3) if first_edit and steps else None,
        first_test_frac=round(first_test.step / steps, 3) if first_test and steps else None,
        last_run_before_submit=pre_submit_runs[-1].test_outcome if pre_submit_runs else None,
        runtime_s=round(max(ts) - t0, 2) if ts and t0 else None,
        time_to_first_test_s=since(first_test),
        time_to_first_edit_s=since(first_edit),
        time_to_submit_s=since(submit),
        patch_chars=len(patch),
        patch_files=p_files,
        patch_lines_added=p_add,
        patch_lines_removed=p_rm,
        patch_touches_tests=p_tests,
    )


def iter_run_trajectories(run_root: Path | str) -> Iterable[tuple[str, Path]]:
    """Yield (model_key, traj_path) for every live trajectory under a run root.

    Layout: ``<run_root>/<model>/<instance_id>/<instance_id>.traj.json``.
    Re-queued infra failures under ``<model>/_infra_failed/`` are skipped.
    """
    root = Path(run_root)
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for traj in sorted(model_dir.glob("*/*.traj.json")):
            if traj.parent.name.startswith("_"):
                continue
            yield model_dir.name, traj


def load_preds(model_dir: Path) -> dict[str, str]:
    path = model_dir / "preds.json"
    if not path.exists():
        return {}
    return {k: (v or {}).get("model_patch") or "" for k, v in json.loads(path.read_text()).items()}


__all__ = ["Action", "TrajFeatures", "extract", "iter_run_trajectories", "load_preds", "parse_actions"]
