"""Parse mini-SWE-agent trajectories and pack K-turn prefixes.

A turn is a user/observation boundary after the initial issue ``q``.
K=0 is issue text only. Early-submit trajectories keep their actual length.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hecate.data.external_miniswe import JoinedLabel
from hecate.router.dataset import RouterExample, Tokenizer, WhitespaceTokenizer, truncate_text

K_MAX = 4
K_EVAL = 3
SUBMIT_MARKERS = ("submit",)


class TrajError(ValueError):
    """Fail-closed trajectory parse or label-match failure."""


@dataclass(frozen=True)
class TrajectoryTurn:
    assistant: str
    observation: str


@dataclass(frozen=True)
class ParsedTrajectory:
    instance_id: str
    query: str
    turns: tuple[TrajectoryTurn, ...]
    submitted_early: bool
    resolved: bool | None

    @property
    def n_turns(self) -> int:
        return len(self.turns)


@dataclass(frozen=True)
class TrajExample:
    instance_id: str
    repo: str
    query: str
    prefixes: tuple[str, ...]
    truncated_at: tuple[bool, ...]
    n_turns: int
    submitted_early: bool
    m1_resolves: bool
    m2_resolves: bool
    traj_resolved: bool | None = None

    def prefix_at(self, k: int) -> str:
        if not self.prefixes:
            return self.query
        index = min(max(k, 0), len(self.prefixes) - 1)
        return self.prefixes[index]

    def truncated_at_k(self, k: int) -> bool:
        if not self.truncated_at:
            return False
        index = min(max(k, 0), len(self.truncated_at) - 1)
        return self.truncated_at[index]

    def to_router_example(self, *, k: int) -> RouterExample:
        return RouterExample(
            instance_id=self.instance_id,
            repo=self.repo,
            text=self.prefix_at(k),
            truncated=self.truncated_at_k(k),
            m1_resolves=self.m1_resolves,
            m2_resolves=self.m2_resolves,
        )


@dataclass(frozen=True)
class LabelMatchReport:
    n_labels: int
    n_trajs: int
    n_matched: int
    missing_from_trajs: tuple[str, ...]
    extra_trajs: tuple[str, ...]
    resolve_mismatches: tuple[str, ...]
    n_with_traj_resolved: int
    provenance: str

    def raise_if_failed(self) -> None:
        if self.missing_from_trajs or self.extra_trajs:
            raise TrajError(
                "instance_id sets do not match labels: "
                f"missing={list(self.missing_from_trajs[:8])} "
                f"extra={list(self.extra_trajs[:8])}"
            )
        if self.resolve_mismatches:
            raise TrajError(
                "traj resolved bits disagree with small_model_resolved: "
                f"{list(self.resolve_mismatches[:8])}"
            )
        if self.n_matched != self.n_labels:
            raise TrajError(
                f"matched {self.n_matched} trajectories, expected {self.n_labels}"
            )


def _as_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(payload, str):
        loaded = json.loads(payload)
        if isinstance(loaded, Mapping):
            return dict(loaded)
    raise TrajError(f"expected mapping trajectory, got {type(payload).__name__}")


def _content(message: Mapping[str, Any]) -> str:
    raw = message.get("content")
    if raw is None:
        raw = message.get("text")
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, Mapping):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(raw or "")


def _role(message: Mapping[str, Any]) -> str:
    return str(message.get("role") or message.get("agent") or "").strip().lower()


def _messages(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("messages", "history", "trajectory"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
        if key == "trajectory" and isinstance(value, Mapping):
            inner = _messages(value)
            if inner:
                return inner
    nested = payload.get("info")
    if isinstance(nested, Mapping):
        inner = nested.get("messages") or nested.get("history")
        if isinstance(inner, list):
            return [item for item in inner if isinstance(item, Mapping)]
    return []


def _instance_id(payload: Mapping[str, Any], fallback: str | None = None) -> str:
    for key in ("instance_id", "instanceId", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    info = payload.get("info")
    if isinstance(info, Mapping):
        value = info.get("instance_id") or info.get("exit_status")
        if info.get("instance_id"):
            return str(info["instance_id"])
    if fallback:
        return fallback
    raise TrajError("trajectory missing instance_id")


def _resolved_bit(payload: Mapping[str, Any]) -> bool | None:
    for key in ("resolved", "small_model_resolved"):
        if key in payload and payload[key] is not None:
            return bool(payload[key])
    info = payload.get("info")
    if isinstance(info, Mapping):
        if "resolved" in info and info["resolved"] is not None:
            return bool(info["resolved"])
        status = str(info.get("exit_status") or "").lower()
        if status in {"submitted", "success", "resolved"}:
            return None
    return None


def _is_submit(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in SUBMIT_MARKERS) and (
        "submit" in lowered.split() or "submit" in lowered
    )


def parse_trajectory(payload: Any, *, fallback_id: str | None = None) -> ParsedTrajectory:
    """Normalize a mini-SWE-agent / HF row into query + observation-bounded turns."""
    root = _as_mapping(payload)
    inner = root.get("trajectory")
    if isinstance(inner, (Mapping, str)):
        body = _as_mapping(inner)
        for key in ("instance_id", "info", "resolved"):
            if key not in body and key in root:
                body[key] = root[key]
    else:
        body = root
    instance_id = _instance_id(body, fallback=fallback_id or root.get("instance_id"))
    messages = _messages(body)
    if not messages:
        query = str(body.get("problem_statement") or body.get("query") or "").strip()
        if not query:
            raise TrajError(f"{instance_id}: no messages and empty query")
        return ParsedTrajectory(
            instance_id=instance_id,
            query=query,
            turns=(),
            submitted_early=True,
            resolved=_resolved_bit(body) if _resolved_bit(body) is not None else _resolved_bit(root),
        )

    query = ""
    turns: list[TrajectoryTurn] = []
    pending_assistant = ""
    for message in messages:
        role = _role(message)
        text = _content(message)
        if role == "system":
            continue
        if role in {"user", "observation"}:
            if not query:
                query = text.strip()
                continue
            if pending_assistant:
                turns.append(TrajectoryTurn(assistant=pending_assistant, observation=text))
                pending_assistant = ""
            continue
        if role in {"assistant", "agent"}:
            if pending_assistant:
                turns.append(TrajectoryTurn(assistant=pending_assistant, observation=""))
            pending_assistant = text
    if pending_assistant:
        turns.append(TrajectoryTurn(assistant=pending_assistant, observation=""))
    if not query.strip():
        raise TrajError(f"{instance_id}: empty issue query")
    n = len(turns)
    last_submit = bool(turns) and _is_submit(turns[-1].assistant)
    submitted_early = n < K_EVAL or (last_submit and n <= K_EVAL)
    resolved = _resolved_bit(body)
    if resolved is None:
        resolved = _resolved_bit(root)
    return ParsedTrajectory(
        instance_id=instance_id,
        query=query.strip(),
        turns=tuple(turns),
        submitted_early=submitted_early,
        resolved=resolved,
    )


def format_prefix(parsed: ParsedTrajectory, k: int) -> str:
    """Issue text plus the first ``k`` observation-bounded turns."""
    if k <= 0 or not parsed.turns:
        return parsed.query
    chunks = [parsed.query]
    for index, turn in enumerate(parsed.turns[:k], start=1):
        chunks.append(f"# Turn {index}\n{turn.assistant}")
        if turn.observation.strip():
            chunks.append(f"# Observation {index}\n{turn.observation}")
    return "\n\n".join(chunks)


def packed_prefixes(
    parsed: ParsedTrajectory,
    *,
    k_max: int = K_MAX,
    tokenizer: Tokenizer | None = None,
    max_tokens: int = 8192,
) -> tuple[tuple[str, ...], tuple[bool, ...]]:
    """Prefixes for K=0..min(k_max, n_turns). Early submit stops at actual length."""
    last_k = min(k_max, parsed.n_turns)
    texts: list[str] = []
    flags: list[bool] = []
    tok = tokenizer
    for k in range(0, last_k + 1):
        raw = format_prefix(parsed, k)
        if tok is None:
            texts.append(raw)
            flags.append(False)
            continue
        clipped, truncated = truncate_text(raw, tok, max_tokens=max_tokens)
        texts.append(clipped)
        flags.append(truncated)
    return tuple(texts), tuple(flags)


def load_traj_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TrajError(f"{path}: expected JSON object")
    return payload


def iter_traj_payloads(root: Path) -> list[tuple[str | None, dict[str, Any]]]:
    """Load ``.traj`` / ``.json`` files or a JSONL dump (HF ``data/full.jsonl``)."""
    target = Path(root)
    rows: list[tuple[str | None, dict[str, Any]]] = []
    if target.is_file():
        if target.suffix == ".jsonl":
            for line in target.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise TrajError(f"{target}: jsonl row is not an object")
                rows.append((str(payload.get("instance_id") or None), payload))
            return rows
        payload = load_traj_file(target)
        return [(str(payload.get("instance_id") or target.stem), payload)]
    if not target.is_dir():
        raise TrajError(f"traj path does not exist: {target}")
    files = sorted(
        p
        for p in target.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".traj", ".json", ".jsonl"}
        and p.name != "provenance.json"
    )
    if not files:
        raise TrajError(f"no trajectory files under {target}")
    for path in files:
        if path.suffix.lower() == ".jsonl":
            rows.extend(iter_traj_payloads(path))
            continue
        payload = load_traj_file(path)
        rows.append((str(payload.get("instance_id") or path.stem), payload))
    return rows


def parse_traj_dir(root: Path) -> dict[str, ParsedTrajectory]:
    parsed: dict[str, ParsedTrajectory] = {}
    for fallback, payload in iter_traj_payloads(root):
        item = parse_trajectory(payload, fallback_id=fallback)
        if item.instance_id in parsed:
            raise TrajError(f"duplicate instance_id {item.instance_id!r}")
        parsed[item.instance_id] = item
    return parsed


def match_traj_labels(
    parsed: Mapping[str, ParsedTrajectory],
    labels: list[JoinedLabel],
    *,
    provenance: str,
) -> LabelMatchReport:
    """Fail-closed 500/500 join. Resolve bits must match when the traj has them."""
    label_ids = {row.instance_id for row in labels}
    traj_ids = set(parsed)
    missing = tuple(sorted(label_ids - traj_ids))
    extra = tuple(sorted(traj_ids - label_ids))
    mismatches: list[str] = []
    n_with_bit = 0
    by_label = {row.instance_id: row for row in labels}
    for instance_id, traj in parsed.items():
        if traj.resolved is None or instance_id not in by_label:
            continue
        n_with_bit += 1
        if bool(traj.resolved) != bool(by_label[instance_id].small_model_resolved):
            mismatches.append(instance_id)
    return LabelMatchReport(
        n_labels=len(labels),
        n_trajs=len(parsed),
        n_matched=len(label_ids & traj_ids),
        missing_from_trajs=missing,
        extra_trajs=extra,
        resolve_mismatches=tuple(sorted(mismatches)),
        n_with_traj_resolved=n_with_bit,
        provenance=provenance,
    )


def build_traj_examples(
    parsed: Mapping[str, ParsedTrajectory],
    labels: list[JoinedLabel],
    *,
    k_max: int = K_MAX,
    tokenizer: Tokenizer | None = None,
    max_tokens: int = 8192,
    provenance: str = "unknown",
) -> tuple[list[TrajExample], LabelMatchReport, dict[str, int]]:
    report = match_traj_labels(parsed, labels, provenance=provenance)
    report.raise_if_failed()
    examples: list[TrajExample] = []
    truncated_k3 = 0
    for row in labels:
        traj = parsed[row.instance_id]
        prefixes, flags = packed_prefixes(
            traj, k_max=k_max, tokenizer=tokenizer, max_tokens=max_tokens
        )
        k3_index = min(K_EVAL, len(prefixes) - 1)
        if flags and flags[k3_index]:
            truncated_k3 += 1
        examples.append(
            TrajExample(
                instance_id=row.instance_id,
                repo=row.repo,
                query=traj.query,
                prefixes=prefixes,
                truncated_at=flags,
                n_turns=traj.n_turns,
                submitted_early=traj.submitted_early,
                m1_resolves=row.small_model_resolved,
                m2_resolves=row.large_model_resolved,
                traj_resolved=traj.resolved,
            )
        )
    counts = {
        "n_examples": len(examples),
        "truncated_k3": truncated_k3,
        "early_submit": sum(1 for ex in examples if ex.submitted_early),
    }
    return examples, report, counts


def eval_examples(examples: list[TrajExample], *, k: int) -> list[RouterExample]:
    return [ex.to_router_example(k=k) for ex in examples]


def train_rows_for_arm(
    examples: list[TrajExample],
    *,
    arm: str,
    k_max: int = K_MAX,
) -> list[tuple[str, bool, str]]:
    """(text, label, instance_id) rows. k0 is query-only; k3 packs K=0..k_max."""
    kind = (arm or "").strip().lower()
    rows: list[tuple[str, bool, str]] = []
    for ex in examples:
        if kind == "k0":
            rows.append((ex.prefix_at(0), ex.m1_resolves, ex.instance_id))
            continue
        if kind != "k3":
            raise TrajError(f"unknown arm {arm!r}; expected k0 or k3")
        last = min(k_max, len(ex.prefixes) - 1)
        for k in range(0, last + 1):
            rows.append((ex.prefixes[k], ex.m1_resolves, ex.instance_id))
    return rows


def truncation_report(
    examples: list[TrajExample],
    *,
    k: int = K_EVAL,
    max_tokens: int = 8192,
    tokenizer: Tokenizer | None = None,
) -> dict[str, Any]:
    tok = tokenizer or WhitespaceTokenizer()
    n = len(examples)
    truncated = 0
    lengths: list[int] = []
    for ex in examples:
        raw_flag = ex.truncated_at_k(k)
        text = ex.prefix_at(k)
        n_tokens = len(tok.encode(text))
        lengths.append(n_tokens)
        if raw_flag or n_tokens > max_tokens:
            truncated += 1
    lengths_sorted = sorted(lengths)
    median = lengths_sorted[len(lengths_sorted) // 2] if lengths_sorted else 0
    return {
        "k": k,
        "max_tokens": max_tokens,
        "n": n,
        "n_truncated": truncated,
        "truncation_rate": (truncated / n) if n else 0.0,
        "median_tokens": median,
        "max_seen_tokens": max(lengths) if lengths else 0,
        "tokenizer": type(tok).__name__,
    }


def second_holdout_repo(examples: list[RouterExample] | list[TrajExample], skip: str) -> str:
    """Largest remaining repo after ``skip``. Fail closed if none remain."""
    counts = Counter(ex.repo for ex in examples if ex.repo != skip)
    if not counts:
        raise TrajError(f"no remaining repos after skipping {skip!r}")
    return counts.most_common(1)[0][0]
