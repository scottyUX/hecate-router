"""Join externally sourced mini-SWE-agent pass/fail labels.

This is a substitute for an in-house matched-scaffold inference run.
It is SWE-bench Verified (500), not Lite (300), and must not be merged
with Qwen 2.5 7B/72B single-shot labels.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

EXPECTED_N = 500
SMALL_PUBLISHED_PCT = 55.4
LARGE_PUBLISHED_PCT = 67.6
SMALL_RESOLVED_COUNT = 277
LARGE_RESOLVED_COUNT = 338

SMALL_SUBMISSION = "20250802_mini-v1.0.0_qwen3-coder-480b-a35b-instruct"
LARGE_SUBMISSION = "20250802_mini-v1.0.0_claude-4-opus-20250514"
SMALL_SOURCE_URL = (
    "https://raw.githubusercontent.com/SWE-bench/experiments/main/"
    f"evaluation/bash-only/{SMALL_SUBMISSION}/per_instance_details.json"
)
LARGE_SOURCE_URL = (
    "https://raw.githubusercontent.com/SWE-bench/experiments/main/"
    f"evaluation/bash-only/{LARGE_SUBMISSION}/per_instance_details.json"
)
SMALL_METADATA_URL = (
    "https://github.com/SWE-bench/experiments/blob/main/"
    f"evaluation/bash-only/{SMALL_SUBMISSION}/metadata.yaml"
)
LARGE_METADATA_URL = (
    "https://github.com/SWE-bench/experiments/blob/main/"
    f"evaluation/bash-only/{LARGE_SUBMISSION}/metadata.yaml"
)

CSV_NAME = "qwen3coder_vs_claude4opus_miniswe_external.csv"
JSON_NAME = "qwen3coder_vs_claude4opus_miniswe_external.json"
TEXT_CSV_NAME = "qwen3coder_vs_claude4opus_with_text.csv"
TEXT_JSON_NAME = "qwen3coder_vs_claude4opus_with_text.json"
FIELDNAMES = (
    "instance_id",
    "repo",
    "small_model_resolved",
    "large_model_resolved",
)
TEXT_FIELDNAMES = (
    "instance_id",
    "repo",
    "small_model_resolved",
    "large_model_resolved",
    "problem_statement",
    "base_commit",
)
BOTH_RESOLVED_COUNT = 258
SMALL_ONLY_COUNT = 19
LARGE_ONLY_COUNT = 80
NEITHER_COUNT = 143
ORACLE_RESOLVED_COUNT = 357
ORACLE_PCT = 71.4
HEADROOM_PP = 3.8

OPUS_GIT_PEEK_IDS = (
    "pylint-dev__pylint-7080",
    "matplotlib__matplotlib-22871",
    "matplotlib__matplotlib-21568",
    "pytest-dev__pytest-6197",
    "pytest-dev__pytest-5840",
    "sympy__sympy-13031",
    "django__django-13513",
)
OPUS_GIT_PEEK_RESOLVED_IDS = (
    "matplotlib__matplotlib-22871",
    "sympy__sympy-13031",
)
# (338 - 2) / 500 if the two resolved git-peek successes were recoded false.
OPUS_GIT_PEEK_SENSITIVITY_PCT = 67.2


class JoinError(ValueError):
    """Fail-closed join or rate-check failure."""


@dataclass(frozen=True)
class JoinedLabel:
    instance_id: str
    repo: str
    small_model_resolved: bool
    large_model_resolved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JoinedLabelWithText:
    instance_id: str
    repo: str
    small_model_resolved: bool
    large_model_resolved: bool
    problem_statement: str
    base_commit: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_repo(instance_id: str) -> str:
    """Map SWE-bench ``owner__name-issue`` to ``owner/name``."""
    if "__" not in instance_id:
        raise JoinError(f"instance_id missing owner separator: {instance_id!r}")
    owner, rest = instance_id.split("__", 1)
    name, sep, issue = rest.rpartition("-")
    if not sep or not name or not issue.isdigit():
        raise JoinError(f"instance_id missing numeric issue suffix: {instance_id!r}")
    return f"{owner}/{name}"


def resolved_map(details: Mapping[str, Any]) -> dict[str, bool]:
    """Return instance_id → resolved from a per_instance_details payload."""
    out: dict[str, bool] = {}
    for instance_id, payload in details.items():
        if not isinstance(payload, Mapping) or "resolved" not in payload:
            raise JoinError(f"missing resolved bit for {instance_id!r}")
        out[str(instance_id)] = bool(payload["resolved"])
    return out


def percent_one_decimal(resolved_count: int, n: int) -> float:
    if n <= 0:
        raise JoinError("cannot compute resolve rate over an empty join")
    return round(100.0 * resolved_count / n, 1)


def join_labels(
    small_details: Mapping[str, Any],
    large_details: Mapping[str, Any],
    *,
    expected_n: int = EXPECTED_N,
    small_published_pct: float = SMALL_PUBLISHED_PCT,
    large_published_pct: float = LARGE_PUBLISHED_PCT,
) -> list[JoinedLabel]:
    """Inner-join two per-instance maps. Fail closed on size or rate mismatch."""
    small = resolved_map(small_details)
    large = resolved_map(large_details)
    small_ids = set(small)
    large_ids = set(large)
    if len(small) != expected_n:
        raise JoinError(
            f"small-model submission has {len(small)} instances, expected {expected_n}"
        )
    if len(large) != expected_n:
        raise JoinError(
            f"large-model submission has {len(large)} instances, expected {expected_n}"
        )
    only_small = sorted(small_ids - large_ids)
    only_large = sorted(large_ids - small_ids)
    if only_small or only_large:
        raise JoinError(
            "instance_id sets do not match: "
            f"only_small={only_small} only_large={only_large}"
        )

    rows = [
        JoinedLabel(
            instance_id=instance_id,
            repo=parse_repo(instance_id),
            small_model_resolved=small[instance_id],
            large_model_resolved=large[instance_id],
        )
        for instance_id in sorted(small_ids)
    ]
    small_resolved = sum(1 for row in rows if row.small_model_resolved)
    large_resolved = sum(1 for row in rows if row.large_model_resolved)
    small_pct = percent_one_decimal(small_resolved, len(rows))
    large_pct = percent_one_decimal(large_resolved, len(rows))
    if small_pct != small_published_pct:
        raise JoinError(
            f"small-model resolve rate {small_pct}% ({small_resolved}/{len(rows)}) "
            f"does not match published {small_published_pct}%"
        )
    if large_pct != large_published_pct:
        raise JoinError(
            f"large-model resolve rate {large_pct}% ({large_resolved}/{len(rows)}) "
            f"does not match published {large_published_pct}%"
        )
    return rows


def complementarity(rows: list[JoinedLabel]) -> dict[str, Any]:
    """Counts for the cost-vs-accuracy framing: headroom is small-only wins."""
    both = sum(
        1 for row in rows if row.small_model_resolved and row.large_model_resolved
    )
    small_only = sum(
        1 for row in rows if row.small_model_resolved and not row.large_model_resolved
    )
    large_only = sum(
        1 for row in rows if not row.small_model_resolved and row.large_model_resolved
    )
    neither = sum(
        1
        for row in rows
        if not row.small_model_resolved and not row.large_model_resolved
    )
    n = len(rows)
    oracle = both + small_only + large_only
    return {
        "n": n,
        "both_resolved": both,
        "small_only": small_only,
        "large_only": large_only,
        "neither": neither,
        "oracle_resolved": oracle,
        "oracle_pct": percent_one_decimal(oracle, n) if n else 0.0,
        "always_small_pct": percent_one_decimal(both + small_only, n) if n else 0.0,
        "always_large_pct": percent_one_decimal(both + large_only, n) if n else 0.0,
        "headroom_pp": percent_one_decimal(small_only, n) if n else 0.0,
        "note": (
            "Headroom vs always-large is the small-only count. Routing value on "
            "this pair is cost (send both-win tasks to the small model), not "
            "accuracy lift over Opus."
        ),
    }


def join_problem_statements(
    labels: list[JoinedLabel],
    by_id: Mapping[str, Mapping[str, Any]],
) -> list[JoinedLabelWithText]:
    """Left-join Verified issue text onto labels. Fail closed; never drop rows."""
    missing = [row.instance_id for row in labels if row.instance_id not in by_id]
    if missing:
        raise JoinError(
            f"{len(missing)} instance_ids missing from SWE-bench Verified: {missing}"
        )
    empty_text: list[str] = []
    empty_commit: list[str] = []
    repo_mismatch: list[str] = []
    out: list[JoinedLabelWithText] = []
    for row in labels:
        payload = by_id[row.instance_id]
        text = str(payload.get("problem_statement") or "")
        commit = str(payload.get("base_commit") or "")
        if not text.strip():
            empty_text.append(row.instance_id)
        if not commit.strip():
            empty_commit.append(row.instance_id)
        verified_repo = payload.get("repo")
        if verified_repo is not None and str(verified_repo) != row.repo:
            repo_mismatch.append(
                f"{row.instance_id}: label={row.repo!r} verified={verified_repo!r}"
            )
        out.append(
            JoinedLabelWithText(
                instance_id=row.instance_id,
                repo=row.repo,
                small_model_resolved=row.small_model_resolved,
                large_model_resolved=row.large_model_resolved,
                problem_statement=text,
                base_commit=commit,
            )
        )
    if empty_text:
        raise JoinError(
            f"{len(empty_text)} empty problem_statement values: {empty_text}"
        )
    if empty_commit:
        raise JoinError(f"{len(empty_commit)} empty base_commit values: {empty_commit}")
    if repo_mismatch:
        raise JoinError(f"repo mismatch vs SWE-bench Verified: {repo_mismatch}")
    return out


def git_peek_sensitivity(rows: list[JoinedLabel]) -> dict[str, Any]:
    """Record Opus git-peek flags and the recode-false rate, computed from rows."""
    by_id = {row.instance_id: row for row in rows}
    missing = [iid for iid in OPUS_GIT_PEEK_IDS if iid not in by_id]
    if missing:
        raise JoinError(f"git-peek instance_ids missing from join: {missing}")
    resolved_flagged = [
        iid for iid in OPUS_GIT_PEEK_IDS if by_id[iid].large_model_resolved
    ]
    if set(resolved_flagged) != set(OPUS_GIT_PEEK_RESOLVED_IDS):
        raise JoinError(
            "git-peek resolved set mismatch: "
            f"got {resolved_flagged}, expected {list(OPUS_GIT_PEEK_RESOLVED_IDS)}"
        )
    recoded = sum(
        1
        for row in rows
        if row.large_model_resolved and row.instance_id not in OPUS_GIT_PEEK_RESOLVED_IDS
    )
    recoded_pct = percent_one_decimal(recoded, len(rows))
    if recoded_pct != OPUS_GIT_PEEK_SENSITIVITY_PCT:
        raise JoinError(
            f"git-peek sensitivity {recoded_pct}% does not match "
            f"expected {OPUS_GIT_PEEK_SENSITIVITY_PCT}%"
        )
    return {
        "flagged_instance_ids": list(OPUS_GIT_PEEK_IDS),
        "flagged_resolved_instance_ids": list(OPUS_GIT_PEEK_RESOLVED_IDS),
        "n_flagged": len(OPUS_GIT_PEEK_IDS),
        "n_flagged_resolved": len(OPUS_GIT_PEEK_RESOLVED_IDS),
        "qwen_git_peek_count": 0,
        "keep_all_rows": True,
        "published_large_resolve_pct": LARGE_PUBLISHED_PCT,
        "sensitivity_recode_false_count": recoded,
        "sensitivity_recode_false_pct": recoded_pct,
        "note": (
            "Seven Opus trajectories were flagged for git log/show/blame. "
            "Two of those resolved. Primary file keeps all 500 so the published "
            f"{LARGE_PUBLISHED_PCT}% still matches. Recoding those two successes "
            f"as false yields ({LARGE_RESOLVED_COUNT} - 2) / {EXPECTED_N} = "
            f"{recoded_pct}% vs {LARGE_PUBLISHED_PCT}% published."
        ),
    }


def write_csv(rows: list[JoinedLabel], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "instance_id": row.instance_id,
                    "repo": row.repo,
                    "small_model_resolved": str(row.small_model_resolved).lower(),
                    "large_model_resolved": str(row.large_model_resolved).lower(),
                }
            )
    return target


def write_json(rows: list[JoinedLabel], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [row.to_dict() for row in rows]
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def read_joined_csv(path: Path | str) -> list[JoinedLabel]:
    target = Path(path)
    rows: list[JoinedLabel] = []
    with target.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(FIELDNAMES):
            raise JoinError(
                f"CSV columns {reader.fieldnames!r} do not match {list(FIELDNAMES)!r}"
            )
        for payload in reader:
            rows.append(
                JoinedLabel(
                    instance_id=payload["instance_id"],
                    repo=payload["repo"],
                    small_model_resolved=_parse_bool(payload["small_model_resolved"]),
                    large_model_resolved=_parse_bool(payload["large_model_resolved"]),
                )
            )
    return rows


def write_text_csv(rows: list[JoinedLabelWithText], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEXT_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "instance_id": row.instance_id,
                    "repo": row.repo,
                    "small_model_resolved": str(row.small_model_resolved).lower(),
                    "large_model_resolved": str(row.large_model_resolved).lower(),
                    "problem_statement": row.problem_statement,
                    "base_commit": row.base_commit,
                }
            )
    return target


def write_text_json(rows: list[JoinedLabelWithText], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [row.to_dict() for row in rows]
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def read_joined_text_csv(path: Path | str) -> list[JoinedLabelWithText]:
    target = Path(path)
    rows: list[JoinedLabelWithText] = []
    with target.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(TEXT_FIELDNAMES):
            raise JoinError(
                f"CSV columns {reader.fieldnames!r} do not match {list(TEXT_FIELDNAMES)!r}"
            )
        for payload in reader:
            rows.append(
                JoinedLabelWithText(
                    instance_id=payload["instance_id"],
                    repo=payload["repo"],
                    small_model_resolved=_parse_bool(payload["small_model_resolved"]),
                    large_model_resolved=_parse_bool(payload["large_model_resolved"]),
                    problem_statement=payload["problem_statement"],
                    base_commit=payload["base_commit"],
                )
            )
    return rows


def join_and_write_text(
    labels: list[JoinedLabel],
    by_id: Mapping[str, Mapping[str, Any]],
    output_dir: Path | str,
) -> tuple[list[JoinedLabelWithText], Path, Path]:
    """Join first, then write. Raises before any text artifact is created."""
    rows = join_problem_statements(labels, by_id)
    target_dir = Path(output_dir)
    csv_path = write_text_csv(rows, target_dir / TEXT_CSV_NAME)
    json_path = write_text_json(rows, target_dir / TEXT_JSON_NAME)
    return rows, csv_path, json_path


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise JoinError(f"expected true/false, got {value!r}")
