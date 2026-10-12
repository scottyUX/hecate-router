#!/usr/bin/env python3
"""Compare the three-model run against the matching SWE-bench leaderboard entries.

For each model, fetches the published mini-SWE-agent "bash only" entry's
per_instance_details.json and (optionally) its trajectories for our 100 tasks,
then reports, per model and on the tasks we graded:
  - resolved rate, ours vs. leaderboard, with per-task agreement, Cohen's
    kappa and exact McNemar on the discordant pairs;
  - by difficulty;
  - cost and API calls per task;
  - with --trajectories: median trajectory features from the same extractor
    (hecate.agent.traj_features) on both sides, plus each side's config.
And the leaderboard's own cross-model overlap and oracle on our 100 tasks.

Reads our side from per_task.csv (scripts/analyze_three_model.py output).
With --baseline-per-task (e.g. r1's per_task.csv when reporting r2), also
compares ours to that earlier run on the tasks both graded.

Usage:
    python scripts/compare_three_model_leaderboard.py \
        --per-task docs/runs/three-model-verified/per_task-interim.csv
    python scripts/compare_three_model_leaderboard.py \
        --per-task data/outputs/runs/three-model-verified-r2/analysis/per_task.csv \
        --tasks-file configs/three_model_tasks_r2.json \
        --baseline-per-task docs/runs/three-model-verified/per_task-interim.csv
    python scripts/compare_three_model_leaderboard.py --trajectories --cache-dir /tmp/lb
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import statistics as st
import sys
import urllib.request
from itertools import combinations
from pathlib import Path

ENTRIES = {
    "opus": "20260217_mini-v2.0.0_claude-4-5-opus-high",
    "gemini": "20260217_mini-v2.0.0_gemini-3-flash-high",
    "minimax": "20260217_mini-v2.0.0_minimax-2-5-high",
}
EXPERIMENTS = "https://raw.githubusercontent.com/SWE-bench/experiments/main/evaluation/verified"
TRAJS = "https://swe-bench-submissions.s3.amazonaws.com/bash-only"
DIFFICULTY = ("<15 min fix", "15 min - 1 hour", "1-4 hours", ">4 hours")
TRAJ_COLS = (
    "steps", "test_runs", "script_runs", "edit_actions", "tracebacks",
    "files_inspected", "first_edit_step", "max_prompt_tokens", "reasoning_tokens", "runtime_s",
)


def _fetch(url: str, dest: Path) -> Path:
    if not dest.exists() or not dest.stat().st_size:
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest)
    return dest


def load_ours(path: Path) -> dict[tuple[str, str], dict]:
    out = {}
    for r in csv.DictReader(path.open()):
        if r["resolved"] in ("True", "False"):
            out[(r["model"], r["instance_id"])] = r
    return out


def _f(v) -> float | None:
    return None if v in (None, "", "None") else float(v)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-task", type=Path, default=Path("data/outputs/runs/three-model-verified/analysis/per_task.csv"))
    parser.add_argument("--tasks-file", type=Path, default=Path("configs/three_model_tasks.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/leaderboard"))
    parser.add_argument("--trajectories", action="store_true", help="also fetch + compare trajectories (~200 MB)")
    parser.add_argument("--baseline-per-task", type=Path, default=None,
                        help="an earlier run's per_task.csv to compare against (paired)")
    parser.add_argument("--out", type=Path, default=None, help="write the markdown report here")
    args = parser.parse_args(argv)

    from hecate.agent.experiment_analysis import cohen_kappa, mcnemar_exact, wilson

    tasks = json.loads(args.tasks_file.read_text())["tasks"]
    ids = [t["instance_id"] for t in tasks]
    diff = {t["instance_id"]: t["difficulty"] for t in tasks}
    ours = load_ours(args.per_task)
    lb = {
        m: json.loads(_fetch(f"{EXPERIMENTS}/{e}/per_instance_details.json", args.cache_dir / e / "per_instance_details.json").read_text())
        for m, e in ENTRIES.items()
    }
    missing = {m: [i for i in ids if i not in lb[m]] for m in ENTRIES}
    if any(missing.values()):
        print(f"error: leaderboard missing ids: {missing}", file=sys.stderr)
        return 1

    n = len(ids)
    L: list[str] = ["# Three-model run vs. SWE-bench leaderboard", ""]
    L += ["Leaderboard entries (mini-SWE-agent, bash only, reasoning effort **high**): "
          + ", ".join(f"`{e}`" for e in ENTRIES.values()) + ".", ""]

    L += ["## Resolved rate, per model", "",
          f"| model | leaderboard on our {n} | tasks we graded | ours | leaderboard | agreement | κ | ours-only / lb-only | McNemar p |",
          "|---|---|---|---|---|---|---|---|---|"]
    detail: list[str] = []
    for m in ENTRIES:
        l100 = [lb[m][i]["resolved"] for i in ids]
        lo, hi = wilson(sum(l100), len(l100))
        both = [i for i in ids if (m, i) in ours]
        o = [ours[(m, i)]["resolved"] == "True" for i in both]
        l = [lb[m][i]["resolved"] for i in both]
        oo = sum(a and not b for a, b in zip(o, l))
        lo_ = sum(b and not a for a, b in zip(o, l))
        L.append(
            f"| {m} | {sum(l100)}/{n} ({100*lo:.0f}–{100*hi:.0f}) | {len(both)} | {sum(o)} ({100*sum(o)/len(both):.1f}%) | "
            f"{sum(l)} ({100*sum(l)/len(both):.1f}%) | {100*sum(a == b for a, b in zip(o, l))/len(both):.1f}% | "
            f"{cohen_kappa(o, l):.2f} | {oo} / {lo_} | {mcnemar_exact(oo, lo_):.3f} |"
        )
        rows = [f"### {m}", "", "| difficulty | n | ours | leaderboard |", "|---|---|---|---|"]
        for d in DIFFICULTY:
            bd = [i for i in both if diff[i] == d]
            if bd:
                rows.append(f"| {d} | {len(bd)} | {sum(ours[(m, i)]['resolved'] == 'True' for i in bd)} | {sum(lb[m][i]['resolved'] for i in bd)} |")
        oc = st.mean(_f(ours[(m, i)]["cost_usd"]) or 0 for i in both)
        lc = st.mean(lb[m][i]["cost"] for i in both)
        ocl = st.mean(_f(ours[(m, i)]["api_calls"]) or 0 for i in both)
        lcl = st.mean(lb[m][i]["api_calls"] for i in both)
        rows += ["", f"Cost/task: ours ${oc:.3f}, leaderboard ${lc:.3f}. API calls/task: ours {ocl:.1f}, leaderboard {lcl:.1f}.", "",
                 "Only we resolved: " + (", ".join(f"`{i}`" for i, a, b in zip(both, o, l) if a and not b) or "none"), "",
                 "Only the leaderboard resolved: " + (", ".join(f"`{i}`" for i, a, b in zip(both, o, l) if b and not a) or "none"), ""]
        detail += rows
    L += ["", *detail]

    if args.trajectories:
        from hecate.agent.traj_features import extract

        def get(a):
            m, i = a
            return _fetch(f"{TRAJS}/{ENTRIES[m]}/trajs/{i}/{i}.traj.json", args.cache_dir / ENTRIES[m] / "trajs" / i / f"{i}.traj.json")

        with cf.ThreadPoolExecutor(24) as ex:
            list(ex.map(get, [(m, i) for m in ENTRIES for i in ids]))
        L += ["## Trajectories (medians, tasks both sides ran)", "",
              "| model | feature | ours | leaderboard |", "|---|---|---|---|"]
        for m, e in ENTRIES.items():
            feats = {}
            for i in ids:
                j = json.loads((args.cache_dir / e / "trajs" / i / f"{i}.traj.json").read_text())
                feats[i] = extract(j, model=m).to_dict()
            both = [i for i in ids if (m, i) in ours]
            for c in TRAJ_COLS:
                a = [v for i in both if (v := _f(ours[(m, i)].get(c))) is not None]
                b = [v for i in both if (v := _f(feats[i][c])) is not None]
                if a and b:
                    L.append(f"| {m} | {c} | {st.median(a):.1f} | {st.median(b):.1f} |")
            cfg = json.loads((args.cache_dir / e / "trajs" / ids[0] / f"{ids[0]}.traj.json").read_text())["info"]["config"]["model"]
            L.append(f"| {m} | leaderboard model config | | `{cfg['model_name']}` {json.dumps(cfg.get('model_kwargs'))} |")
        L.append("")

    if args.baseline_per_task:
        base = load_ours(args.baseline_per_task)
        L += [f"## Ours vs. baseline run (`{args.baseline_per_task}`)", "",
              "| model | tasks both graded | ours | baseline | agreement | ours-only / baseline-only | McNemar p | cost/task ours / baseline | calls/task ours / baseline |",
              "|---|---|---|---|---|---|---|---|---|"]
        for m in ENTRIES:
            both = [i for i in ids if (m, i) in ours and (m, i) in base]
            if not both:
                L.append(f"| {m} | 0 | | | | | | | |")
                continue
            o = [ours[(m, i)]["resolved"] == "True" for i in both]
            b = [base[(m, i)]["resolved"] == "True" for i in both]
            oo = sum(x and not y for x, y in zip(o, b))
            bo = sum(y and not x for x, y in zip(o, b))
            cost = [st.mean(_f(r[(m, i)]["cost_usd"]) or 0 for i in both) for r in (ours, base)]
            calls = [st.mean(_f(r[(m, i)]["api_calls"]) or 0 for i in both) for r in (ours, base)]
            L.append(
                f"| {m} | {len(both)} | {sum(o)} ({100*sum(o)/len(both):.1f}%) | {sum(b)} ({100*sum(b)/len(both):.1f}%) | "
                f"{100*sum(x == y for x, y in zip(o, b))/len(both):.1f}% | {oo} / {bo} | {mcnemar_exact(oo, bo):.3f} | "
                f"${cost[0]:.3f} / ${cost[1]:.3f} | {calls[0]:.1f} / {calls[1]:.1f} |"
            )
        L.append("")

    L += [f"## Leaderboard's own cross-model view on our {n}", ""]
    solved = {i: {m for m in ENTRIES if lb[m][i]["resolved"]} for i in ids}
    oracle = sum(min(lb[m][i]["cost"] for m in ([m for m in ENTRIES if lb[m][i]["resolved"]] or ENTRIES)) for i in ids)
    L += [f"- All three: {sum(len(s) == 3 for s in solved.values())}; none: {sum(not s for s in solved.values())}; only one: "
          + ", ".join(f"{m} {sum(s == {m} for s in solved.values())}" for m in ENTRIES),
          f"- Oracle (cheapest resolving model): {sum(bool(s) for s in solved.values())}/{n} for ${oracle:.2f}; "
          + ", ".join(f"always-{m} {sum(lb[m][i]['resolved'] for i in ids)}/{n} for ${sum(lb[m][i]['cost'] for i in ids):.2f}" for m in ENTRIES)]
    for a, b in combinations(ENTRIES, 2):
        va = [lb[a][i]["resolved"] for i in ids]
        vb = [lb[b][i]["resolved"] for i in ids]
        ao = sum(x and not y for x, y in zip(va, vb))
        bo = sum(y and not x for x, y in zip(va, vb))
        L.append(f"- {a} vs {b}: κ {cohen_kappa(va, vb):.2f}, {a}-only {ao} / {b}-only {bo}, McNemar p {mcnemar_exact(ao, bo):.3f}")

    report = "\n".join(L) + "\n"
    if args.out:
        args.out.write_text(report)
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
