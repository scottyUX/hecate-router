"""Analysis for the three-model SWE-bench Verified experiment.

Joins, per (model, task): run status (infra failure vs. real attempt), the
graded outcome from ``executions.jsonl``, cost, and trajectory features; then
reports per-model performance and efficiency, cross-model overlap, and how
trajectory features separate resolved from unresolved runs.

Denominators are explicit everywhere. A task that never reached the model
(no trajectory) is an infra failure and is excluded from resolved rates, never
counted as a model failure. Ungraded attempts are reported, not guessed.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from hecate.agent.traj_features import extract, load_preds
from hecate.router.metrics import auroc

DIFFICULTY_ORDER = ("<15 min fix", "15 min - 1 hour", "1-4 hours", ">4 hours")

# Features compared between resolved and unresolved runs. Excludes identifiers,
# the outcome itself, and patch_* (properties of the answer, not the process).
PROCESS_FEATURES = (
    "steps", "api_calls", "actions", "actions_per_step", "format_errors",
    "cost_usd", "prompt_tokens", "completion_tokens", "reasoning_tokens",
    "max_prompt_tokens", "inspect_actions", "search_actions", "edit_actions",
    "revert_actions", "test_runs", "test_runs_passed", "test_runs_failed",
    "script_runs", "script_runs_passed", "script_runs_failed", "files_inspected",
    "files_written", "helper_files_written", "nonzero_returncodes", "tracebacks",
    "timeouts", "edit_run_cycles", "failed_run_then_edit", "first_edit_step",
    "first_test_step", "first_edit_frac", "first_test_frac", "runtime_s",
    "time_to_first_test_s", "time_to_first_edit_s", "time_to_submit_s",
)


@dataclass
class Run:
    model: str
    instance_id: str
    repo: str
    difficulty: str
    status: str  # attempted | infra | missing
    resolved: bool | None = None  # None = not graded (yet)
    patch_applied: bool | None = None
    exit_status: str | None = None
    cost_usd: float | None = None  # OpenRouter-billed when available
    features: dict[str, Any] = field(default_factory=dict)

    @property
    def graded(self) -> bool:
        return self.status == "attempted" and self.resolved is not None


# ---------------------------------------------------------------- statistics


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


# ---------------------------------------------------------------- loading


def load_executions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["instance_id"]] = rec
    return out


def load_runs(run_root: Path, tasks: list[dict[str, Any]], models: Iterable[str]) -> list[Run]:
    runs: list[Run] = []
    for model in models:
        model_dir = run_root / model
        preds = load_preds(model_dir)
        execs = load_executions(model_dir / "executions.jsonl")
        for task in tasks:
            iid = task["instance_id"]
            run = Run(model, iid, task["repo"], task["difficulty"], status="missing")
            traj_path = model_dir / iid / f"{iid}.traj.json"
            if iid in preds and not traj_path.exists():
                run.status = "infra"
            elif traj_path.exists():
                run.status = "attempted"
                traj = json.loads(traj_path.read_text())
                feats = extract(traj, model=model, patch=preds.get(iid)).to_dict()
                run.features = feats
                run.exit_status = feats["exit_status"]
                run.cost_usd = feats["openrouter_cost_usd"] or feats["cost_usd"]
                rec = execs.get(iid)
                if rec is not None:
                    run.resolved = bool(rec.get("resolved"))
                    run.patch_applied = rec.get("patch_applied")
            runs.append(run)
    return runs


# ---------------------------------------------------------------- analyses


def _rate(runs: list[Run]) -> dict[str, Any]:
    graded = [r for r in runs if r.graded]
    k = sum(1 for r in graded if r.resolved)
    ci = wilson(k, len(graded))
    return {
        "resolved": k,
        "graded": len(graded),
        "rate": k / len(graded) if graded else None,
        "ci95": ci,
    }


def per_model(runs: list[Run], models: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for m in models:
        rs = [r for r in runs if r.model == m]
        att = [r for r in rs if r.status == "attempted"]
        graded = [r for r in att if r.graded]
        resolved = [r for r in graded if r.resolved]
        costs = [r.cost_usd for r in att if r.cost_usd is not None]
        calls = [r.features["api_calls"] for r in att if r.features.get("api_calls") is not None]
        rt = [r.features["runtime_s"] for r in att if r.features.get("runtime_s") is not None]
        steps = [r.features["steps"] for r in att]
        total = sum(costs)
        out[m] = {
            "tasks": len(rs),
            "attempted": len(att),
            "infra_failures": sum(1 for r in rs if r.status == "infra"),
            "missing": sum(1 for r in rs if r.status == "missing"),
            "ungraded": len(att) - len(graded),
            "exit_status": dict(Counter(r.exit_status or "?" for r in att)),
            "patch_applied": sum(1 for r in graded if r.patch_applied),
            **_rate(rs),
            "by_difficulty": {
                d: _rate([r for r in rs if r.difficulty == d])
                for d in DIFFICULTY_ORDER
                if any(r.difficulty == d for r in rs)
            },
            "by_repo": {
                repo: _rate([r for r in rs if r.repo == repo])
                for repo, _ in Counter(r.repo for r in rs).most_common()
            },
            "total_cost_usd": round(total, 4),
            "cost_per_task_usd": round(total / len(costs), 4) if costs else None,
            "cost_per_resolved_usd": round(
                sum(r.cost_usd or 0 for r in graded) / len(resolved), 4
            ) if resolved else None,
            "api_calls_mean": round(mean(calls), 2) if calls else None,
            "api_calls_median": median(calls) if calls else None,
            "steps_mean": round(mean(steps), 2) if steps else None,
            "runtime_s_mean": round(mean(rt), 1) if rt else None,
            "runtime_s_median": round(median(rt), 1) if rt else None,
        }
    return out


def cross_model(runs: list[Run], models: list[str]) -> dict[str, Any]:
    """Overlap on tasks graded for every model (the only fair comparison set)."""
    by = {(r.model, r.instance_id): r for r in runs}
    ids = sorted({r.instance_id for r in runs})
    common = [i for i in ids if all(by[(m, i)].graded for m in models)]
    solved = {i: frozenset(m for m in models if by[(m, i)].resolved) for i in common}

    only = {m: sorted(i for i in common if solved[i] == {m}) for m in models}
    exactly_two = {
        f"{a}+{b}": sorted(i for i in common if solved[i] == {a, b})
        for a, b in combinations(models, 2)
    }
    pairwise = {}
    for a, b in combinations(models, 2):
        va = [by[(a, i)].resolved for i in common]
        vb = [by[(b, i)].resolved for i in common]
        a_only = sum(1 for x, y in zip(va, vb) if x and not y)
        b_only = sum(1 for x, y in zip(va, vb) if y and not x)
        pairwise[f"{a} vs {b}"] = {
            "n": len(common),
            "agreement": round(sum(x == y for x, y in zip(va, vb)) / len(common), 3) if common else None,
            "kappa": round(k, 3) if (k := cohen_kappa(va, vb)) is not None else None,
            f"{a}_only": a_only,
            f"{b}_only": b_only,
            "mcnemar_p": round(mcnemar_exact(a_only, b_only), 4),
        }

    # Oracle router: per task, the cheapest model that resolves it; if none
    # does, the cheapest attempt (a router still has to send it somewhere).
    oracle_cost = 0.0
    for i in common:
        cands = [by[(m, i)] for m in models if by[(m, i)].resolved] or [by[(m, i)] for m in models]
        oracle_cost += min(r.cost_usd or 0.0 for r in cands)
    single_cost = {m: round(sum(by[(m, i)].cost_usd or 0 for i in common), 4) for m in models}
    single_rate = {
        m: (sum(1 for i in common if by[(m, i)].resolved) / len(common)) if common else None
        for m in models
    }
    any_solved = sum(1 for i in common if solved[i])
    return {
        "n_common": len(common),
        "all_solved": sum(1 for i in common if len(solved[i]) == len(models)),
        "none_solved": sum(1 for i in common if not solved[i]),
        "only_one": {m: len(v) for m, v in only.items()},
        "only_one_ids": only,
        "exactly_two": {k: len(v) for k, v in exactly_two.items()},
        "exactly_two_ids": exactly_two,
        "pairwise": pairwise,
        "oracle": {
            "resolved_rate": any_solved / len(common) if common else None,
            "cost_usd": round(oracle_cost, 4),
            "single_model_rate": single_rate,
            "single_model_cost_usd": single_cost,
        },
    }


def feature_separation(
    runs: list[Run], models: list[str], features: Iterable[str] = PROCESS_FEATURES
) -> dict[str, list[dict[str, Any]]]:
    """Per model (and pooled): AUROC of each feature for resolved vs not.

    AUROC 0.5 = no separation; >0.5 = higher values go with resolved runs.
    Pooled mixes models with very different base rates and styles, so read it
    as "does this signal survive across models", not as a single effect.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    groups = {m: [r for r in runs if r.model == m and r.graded] for m in models}
    groups["pooled"] = [r for r in runs if r.graded]
    for name, rs in groups.items():
        rows = []
        for f in features:
            pairs = [(r.resolved, r.features.get(f)) for r in rs if r.features.get(f) is not None]
            labels = [bool(y) for y, _ in pairs]
            vals = [float(v) for _, v in pairs]
            auc = auroc(labels, vals) if pairs else None
            pos = [v for y, v in zip(labels, vals) if y]
            neg = [v for y, v in zip(labels, vals) if not y]
            rows.append({
                "feature": f,
                "n": len(pairs),
                "auroc": round(auc, 3) if auc is not None else None,
                "mean_resolved": round(mean(pos), 3) if pos else None,
                "mean_unresolved": round(mean(neg), 3) if neg else None,
            })
        # `is None`, not `or`: an AUROC of 0.0 is the strongest signal, not "none".
        rows.sort(key=lambda x: -abs((0.5 if x["auroc"] is None else x["auroc"]) - 0.5))
        out[name] = rows
    return out


def per_task_rows(runs: list[Run]) -> list[dict[str, Any]]:
    """Long table, one row per (model, task): the master table for routing."""
    rows = []
    for r in runs:
        rows.append({
            "model": r.model,
            "instance_id": r.instance_id,
            "repo": r.repo,
            "difficulty": r.difficulty,
            "status": r.status,
            "resolved": r.resolved,
            "patch_applied": r.patch_applied,
            "exit_status": r.exit_status,
            "cost_usd": r.cost_usd,
            **{f: r.features.get(f) for f in PROCESS_FEATURES if f != "cost_usd"},
        })
    return rows


# ---------------------------------------------------------------- report


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _rate_cell(d: dict[str, Any]) -> str:
    if not d["graded"]:
        return "–"
    lo, hi = d["ci95"]
    return f"{d['resolved']}/{d['graded']} ({_pct(d['rate'])}, {100*lo:.0f}–{100*hi:.0f})"


def render_markdown(summary: dict[str, Any], models: list[str], top_features: int = 10) -> str:
    pm, xm, fs = summary["per_model"], summary["cross_model"], summary["features"]
    L: list[str] = ["# Three-model SWE-bench Verified: analysis", ""]
    L += [f"Generated {summary['generated']}. Tasks: {summary['n_tasks']} "
          f"(`{summary['tasks_file']}`). Resolved rates exclude infra failures and "
          "ungraded runs; brackets are Wilson 95% CIs.", ""]

    L += ["## Coverage", "", "| model | attempted | infra failures | missing | ungraded | exit statuses |",
          "|---|---|---|---|---|---|"]
    for m in models:
        p = pm[m]
        ex = ", ".join(f"{k} {v}" for k, v in sorted(p["exit_status"].items()))
        L.append(f"| {m} | {p['attempted']} | {p['infra_failures']} | {p['missing']} | {p['ungraded']} | {ex} |")

    L += ["", "## Resolved rate", "", "| model | overall | " + " | ".join(DIFFICULTY_ORDER) + " |",
          "|---|---|" + "---|" * len(DIFFICULTY_ORDER)]
    for m in models:
        p = pm[m]
        cells = [_rate_cell(p["by_difficulty"][d]) if d in p["by_difficulty"] else "–" for d in DIFFICULTY_ORDER]
        L.append(f"| {m} | {_rate_cell(p)} | " + " | ".join(cells) + " |")

    repos = list(pm[models[0]]["by_repo"])
    L += ["", "### By repo", "", "| repo | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for repo in repos:
        L.append(f"| {repo} | " + " | ".join(_rate_cell(pm[m]["by_repo"][repo]) for m in models) + " |")

    L += ["", "## Efficiency", "",
          "| model | total $ | $/task | $/resolved | API calls (mean / median) | steps (mean) | runtime s (mean / median) |",
          "|---|---|---|---|---|---|---|"]
    for m in models:
        p = pm[m]
        L.append(f"| {m} | {p['total_cost_usd']} | {p['cost_per_task_usd']} | {p['cost_per_resolved_usd']} | "
                 f"{p['api_calls_mean']} / {p['api_calls_median']} | {p['steps_mean']} | "
                 f"{p['runtime_s_mean']} / {p['runtime_s_median']} |")

    L += ["", f"## Cross-model (n={xm['n_common']} tasks graded for all models)", "",
          f"- Solved by all: **{xm['all_solved']}**",
          f"- Solved by none: **{xm['none_solved']}**",
          "- Solved by only one: " + ", ".join(f"{m} **{n}**" for m, n in xm["only_one"].items()),
          "- Solved by exactly two: " + ", ".join(f"{k} **{n}**" for k, n in xm["exactly_two"].items()),
          "", "| pair | agreement | Cohen's κ | discordant | McNemar p |", "|---|---|---|---|---|"]
    for pair, d in xm["pairwise"].items():
        a, b = pair.split(" vs ")
        L.append(f"| {pair} | {_pct(d['agreement'])} | {d['kappa']} | {a} {d[f'{a}_only']} / {b} {d[f'{b}_only']} | {d['mcnemar_p']} |")
    o = xm["oracle"]
    L += ["", "**Oracle router** (per task, cheapest model that resolves it): "
          f"{_pct(o['resolved_rate'])} resolved for ${o['cost_usd']}, vs. single models: "
          + ", ".join(f"{m} {_pct(o['single_model_rate'][m])} for ${o['single_model_cost_usd'][m]}" for m in models)
          + ". This is the routing headroom on this task set."]

    L += ["", "## Trajectory features vs. outcome", "",
          f"AUROC of each process feature for resolved vs. unresolved (0.5 = no signal; "
          f">0.5 = higher with resolved). Top {top_features} by distance from 0.5. "
          "Small n per model: treat as exploratory.", ""]
    for name in [*models, "pooled"]:
        L += [f"### {name}", "", "| feature | AUROC | mean resolved | mean unresolved | n |", "|---|---|---|---|---|"]
        for row in fs[name][:top_features]:
            L.append(f"| {row['feature']} | {row['auroc']} | {row['mean_resolved']} | {row['mean_unresolved']} | {row['n']} |")
        L.append("")
    return "\n".join(L) + "\n"


__all__ = [
    "PROCESS_FEATURES", "Run", "cohen_kappa", "cross_model", "feature_separation",
    "load_runs", "mcnemar_exact", "per_model", "per_task_rows", "render_markdown", "wilson",
]
