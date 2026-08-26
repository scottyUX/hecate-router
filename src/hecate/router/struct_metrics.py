"""Python AST structural metrics on oracle files (v2 ceiling; localization leak)."""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from hecate.data.tasks import SwebenchTask
from hecate.scaffold.context import ContextFile, load_oracle_files_uncapped

METRIC_NAMES: tuple[str, ...] = (
    "n_files",
    "n_functions",
    "n_imports",
    "loc",
    "mean_cyclo",
    "max_cyclo",
    "mean_nest",
    "max_nest",
    "mean_fn_loc",
    "max_fn_loc",
    "mean_arity",
    "parse_errors",
)

_FEATURES_TEXT = "text"
_FEATURES_METRICS = "metrics"
_FEATURES_FUSION = "fusion"
FEATURE_ARMS = (_FEATURES_TEXT, _FEATURES_METRICS, _FEATURES_FUSION)


@dataclass(frozen=True)
class MetricScaler:
    mean: tuple[float, ...]
    std: tuple[float, ...]

    def transform(self, vector: Sequence[float]) -> list[float]:
        if len(vector) != len(self.mean):
            raise ValueError(
                f"metric vector length {len(vector)} != scaler {len(self.mean)}"
            )
        out: list[float] = []
        for value, mean, std in zip(vector, self.mean, self.std, strict=True):
            if std < 1e-8:
                out.append(0.0)
            else:
                out.append((float(value) - mean) / std)
        return out


def fit_metric_scaler(vectors: Sequence[Sequence[float]]) -> MetricScaler:
    if not vectors:
        raise ValueError("cannot fit scaler on zero metric vectors")
    width = len(vectors[0])
    if any(len(row) != width for row in vectors):
        raise ValueError("metric vectors must share one length")
    n = len(vectors)
    means: list[float] = []
    stds: list[float] = []
    for col in range(width):
        vals = [float(row[col]) for row in vectors]
        mean = sum(vals) / n
        if n == 1:
            std = 0.0
        else:
            var = sum((x - mean) ** 2 for x in vals) / (n - 1)
            std = math.sqrt(var)
        means.append(mean)
        stds.append(std)
    return MetricScaler(mean=tuple(means), std=tuple(stds))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _max_or_zero(values: list[float]) -> float:
    return max(values) if values else 0.0


class _FunctionStats(ast.NodeVisitor):
    def __init__(self) -> None:
        self.cyclo = 1
        self.max_nest = 0
        self._nest = 0

    def _push(self, node: ast.AST) -> None:
        self._nest += 1
        self.max_nest = max(self.max_nest, self._nest)
        self.generic_visit(node)
        self._nest -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_For(self, node: ast.For) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_While(self, node: ast.While) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_With(self, node: ast.With) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.cyclo += 1
        self._push(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.cyclo += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.cyclo += max(len(node.values) - 1, 0)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.cyclo += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.cyclo += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.cyclo += max(len(node.cases), 0)
        self._push(node)


def _arity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = node.args
    return (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )


def _fn_loc(node: ast.AST) -> int:
    start = getattr(node, "lineno", 1) or 1
    end = getattr(node, "end_lineno", start) or start
    return max(end - start + 1, 1)


def metrics_from_python_source(source: str) -> dict[str, float]:
    """Per-file stats. Unparseable source returns zeros plus parse_errors=1."""
    loc = len(source.splitlines()) if source else 0
    empty = {
        "n_functions": 0.0,
        "n_imports": 0.0,
        "loc": float(loc),
        "mean_cyclo": 0.0,
        "max_cyclo": 0.0,
        "mean_nest": 0.0,
        "max_nest": 0.0,
        "mean_fn_loc": 0.0,
        "max_fn_loc": 0.0,
        "mean_arity": 0.0,
        "parse_errors": 0.0,
    }
    if not source.strip():
        return empty
    try:
        tree = ast.parse(source)
    except SyntaxError:
        empty["parse_errors"] = 1.0
        return empty
    imports = 0
    cyclos: list[float] = []
    nests: list[float] = []
    fn_locs: list[float] = []
    arities: list[float] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _FunctionStats()
            for child in ast.iter_child_nodes(node):
                visitor.visit(child)
            cyclos.append(float(visitor.cyclo))
            nests.append(float(visitor.max_nest))
            fn_locs.append(float(_fn_loc(node)))
            arities.append(float(_arity(node)))
    empty.update(
        {
            "n_functions": float(len(cyclos)),
            "n_imports": float(imports),
            "mean_cyclo": _mean(cyclos),
            "max_cyclo": _max_or_zero(cyclos),
            "mean_nest": _mean(nests),
            "max_nest": _max_or_zero(nests),
            "mean_fn_loc": _mean(fn_locs),
            "max_fn_loc": _max_or_zero(fn_locs),
            "mean_arity": _mean(arities),
        }
    )
    return empty


def metrics_from_files(files: Sequence[ContextFile]) -> dict[str, float]:
    n_files = float(len(files))
    if not files:
        return {name: 0.0 for name in METRIC_NAMES}
    per_file = [metrics_from_python_source(item.content) for item in files]
    n_functions = sum(row["n_functions"] for row in per_file)
    n_imports = sum(row["n_imports"] for row in per_file)
    loc = sum(row["loc"] for row in per_file)
    parse_errors = sum(row["parse_errors"] for row in per_file)
    weighted_cyclo = [
        row["mean_cyclo"] for row in per_file if row["n_functions"] > 0
    ]
    # Prefer function-level max across files, not mean-of-means only.
    max_cyclo = max((row["max_cyclo"] for row in per_file), default=0.0)
    max_nest = max((row["max_nest"] for row in per_file), default=0.0)
    max_fn_loc = max((row["max_fn_loc"] for row in per_file), default=0.0)
    fn_means = [row["mean_fn_loc"] for row in per_file if row["n_functions"] > 0]
    nest_means = [row["mean_nest"] for row in per_file if row["n_functions"] > 0]
    arity_means = [row["mean_arity"] for row in per_file if row["n_functions"] > 0]
    return {
        "n_files": n_files,
        "n_functions": n_functions,
        "n_imports": n_imports,
        "loc": loc,
        "mean_cyclo": _mean(weighted_cyclo),
        "max_cyclo": max_cyclo,
        "mean_nest": _mean(nest_means),
        "max_nest": max_nest,
        "mean_fn_loc": _mean(fn_means),
        "max_fn_loc": max_fn_loc,
        "mean_arity": _mean(arity_means),
        "parse_errors": parse_errors,
    }


def vector_from_metrics(payload: dict[str, float]) -> list[float]:
    return [float(payload.get(name, 0.0)) for name in METRIC_NAMES]


def metrics_for_task(
    task: SwebenchTask,
    *,
    cache_dir: Path | str | None = None,
) -> dict[str, float]:
    files = load_oracle_files_uncapped(task, cache_dir=cache_dir)
    return metrics_from_files(files)


def default_metric_cache_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "outputs" / "cache" / "oracle_file_metrics.json"


def load_metric_cache(path: Path) -> dict[str, list[float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("vectors") if isinstance(payload, dict) else payload
    if not isinstance(rows, dict):
        raise ValueError(f"metric cache must be a mapping: {path}")
    out: dict[str, list[float]] = {}
    for key, value in rows.items():
        vec = [float(x) for x in value]
        if len(vec) != len(METRIC_NAMES):
            raise ValueError(
                f"{key}: expected {len(METRIC_NAMES)} metrics, got {len(vec)}"
            )
        out[str(key)] = vec
    return out


def write_metric_cache(path: Path, vectors: dict[str, list[float]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "oracle_leak": True,
        "metric_names": list(METRIC_NAMES),
        "n": len(vectors),
        "vectors": vectors,
    }
    path.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def build_oracle_metric_vectors(
    tasks: Iterable[SwebenchTask],
    instance_ids: Sequence[str],
    *,
    cache_path: Path | None = None,
    cache_dir: Path | str | None = None,
    reuse_cache: bool = True,
) -> dict[str, list[float]]:
    """Fail-closed: every instance_id gets a vector; extras in cache are ignored."""
    wanted = list(instance_ids)
    path = cache_path if cache_path is not None else default_metric_cache_path()
    if reuse_cache and path.is_file():
        cached = load_metric_cache(path)
        missing = [iid for iid in wanted if iid not in cached]
        if not missing:
            return {iid: cached[iid] for iid in wanted}
    by_id = {task.instance_id: task for task in tasks}
    missing_tasks = [iid for iid in wanted if iid not in by_id]
    if missing_tasks:
        raise ValueError(
            f"{len(missing_tasks)} instance_id(s) missing from Verified tasks: "
            f"{missing_tasks[:5]}"
        )
    vectors: dict[str, list[float]] = {}
    if reuse_cache and path.is_file():
        try:
            vectors.update(load_metric_cache(path))
        except ValueError:
            vectors = {}
    computed = 0
    for iid in wanted:
        if iid in vectors:
            continue
        vectors[iid] = vector_from_metrics(
            metrics_for_task(by_id[iid], cache_dir=cache_dir)
        )
        computed += 1
        if computed == 1 or computed % 25 == 0:
            print(f"[oracle metrics] computed {computed}, joined {len(wanted)}", flush=True)
    if len(vectors) < len(wanted) or any(iid not in vectors for iid in wanted):
        raise ValueError("oracle metric join is not 500/500 fail-closed")
    write_metric_cache(path, {iid: vectors[iid] for iid in wanted})
    return {iid: vectors[iid] for iid in wanted}


def assemble_features(
    instance_ids: Sequence[str],
    *,
    features: str,
    cls: dict[str, list[float]] | None,
    metrics: dict[str, list[float]] | None,
    scaler: MetricScaler | None,
) -> list[list[float]]:
    """Build one feature row per id. Metrics are scaled when a scaler is given."""
    mode = (features or _FEATURES_TEXT).strip()
    if mode not in FEATURE_ARMS:
        raise ValueError(f"unknown features {mode!r}")
    rows: list[list[float]] = []
    for iid in instance_ids:
        if mode == _FEATURES_TEXT:
            if cls is None or iid not in cls:
                raise KeyError(f"missing CLS vector for {iid}")
            rows.append(list(cls[iid]))
            continue
        if metrics is None or iid not in metrics:
            raise KeyError(f"missing metric vector for {iid}")
        metric_vec = list(metrics[iid])
        if scaler is not None:
            metric_vec = scaler.transform(metric_vec)
        if mode == _FEATURES_METRICS:
            rows.append(metric_vec)
            continue
        if cls is None or iid not in cls:
            raise KeyError(f"missing CLS vector for {iid}")
        rows.append(list(cls[iid]) + metric_vec)
    return rows


def oracle_leak_for(features: str) -> bool:
    return features in {_FEATURES_METRICS, _FEATURES_FUSION}
