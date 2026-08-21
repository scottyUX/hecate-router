"""Stage-3 routing labels and E-M4 pre-flight metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from hecate.data import GenerationRecord

BOTH = "both"
ONLY_M1 = "only_m1"
ONLY_M2 = "only_m2"
NEITHER = "neither"
_BUCKETS = (BOTH, ONLY_M1, ONLY_M2, NEITHER)


@dataclass(frozen=True)
class RoutingLabel:
    instance_id: str
    repo: str
    m1_slug: str
    m2_slug: str
    m1_resolves: bool
    m2_resolves: bool
    complementarity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def complementarity_bucket(m1_resolves: bool, m2_resolves: bool) -> str:
    if m1_resolves and m2_resolves:
        return BOTH
    if m1_resolves:
        return ONLY_M1
    if m2_resolves:
        return ONLY_M2
    return NEITHER


def build_labels(
    records: list[GenerationRecord],
    *,
    m1_slug: str,
    m2_slug: str,
    positive_rate_threshold: float = 0.15,
) -> tuple[list[RoutingLabel], dict[str, Any]]:
    """Return label rows and a pre-flight report dict."""
    m1_by_id: dict[str, GenerationRecord] = {}
    m2_by_id: dict[str, GenerationRecord] = {}
    for record in records:
        if record.model_slug == m1_slug:
            m1_by_id[record.instance_id] = record
        elif record.model_slug == m2_slug:
            m2_by_id[record.instance_id] = record

    all_ids = sorted(set(m1_by_id) | set(m2_by_id))
    incomplete = [iid for iid in all_ids if iid not in m1_by_id or iid not in m2_by_id]
    complete_ids = [iid for iid in all_ids if iid not in incomplete]

    labels: list[RoutingLabel] = []
    mismatched: list[str] = []
    buckets = {key: 0 for key in _BUCKETS}
    m1_resolved = 0
    m2_resolved = 0
    oracle = 0

    for instance_id in complete_ids:
        m1 = m1_by_id[instance_id]
        m2 = m2_by_id[instance_id]
        if m1.prompt_hash != m2.prompt_hash:
            mismatched.append(instance_id)
        m1_ok = m1.resolved is True
        m2_ok = m2.resolved is True
        bucket = complementarity_bucket(m1_ok, m2_ok)
        buckets[bucket] += 1
        if m1_ok:
            m1_resolved += 1
        if m2_ok:
            m2_resolved += 1
        if m1_ok or m2_ok:
            oracle += 1
        labels.append(
            RoutingLabel(
                instance_id=instance_id,
                repo=m1.repo or m2.repo,
                m1_slug=m1_slug,
                m2_slug=m2_slug,
                m1_resolves=m1_ok,
                m2_resolves=m2_ok,
                complementarity=bucket,
            )
        )

    n_tasks = len(complete_ids)
    m1_rate = (m1_resolved / n_tasks) if n_tasks else 0.0
    m2_rate = (m2_resolved / n_tasks) if n_tasks else 0.0
    oracle_rate = (oracle / n_tasks) if n_tasks else 0.0
    headroom = oracle_rate - m2_rate

    preflight: dict[str, Any] = {
        "n_tasks": n_tasks,
        "incomplete_instance_ids": incomplete,
        "m1_slug": m1_slug,
        "m2_slug": m2_slug,
        "shared_scaffold": {
            "ok": not mismatched,
            "mismatched_instance_ids": mismatched,
        },
        "m1_resolve_rate": m1_rate,
        "m2_resolve_rate": m2_rate,
        "complementarity": buckets,
        "always_m1_resolve_rate": m1_rate,
        "always_m2_resolve_rate": m2_rate,
        "oracle_routing_resolve_rate": oracle_rate,
        "routing_headroom": headroom,
        "m1_positive_rate": m1_rate,
        "m1_positive_rate_flag": m1_rate < positive_rate_threshold,
        "m1_positive_rate_threshold": positive_rate_threshold,
    }
    return labels, preflight
