"""BIDS-style run IDs: exp-02_arm-k1_split-specialist_seed-0."""

from __future__ import annotations

import re

_ENTITY = re.compile(r"^[a-z0-9]+$")
_PAIR = re.compile(r"^([a-z]+)-([a-z0-9]+)$")


class RunIdError(ValueError):
    """Fail-closed run-id parse or format error."""


def _entity(value: str, *, field: str) -> str:
    text = (value or "").strip().lower().replace("_", "").replace("-", "").replace("/", "")
    if not text or not _ENTITY.fullmatch(text):
        raise RunIdError(f"invalid {field} {value!r}; use letters/digits only after stripping -_/")
    return text


def make_run_id(
    *,
    exp: int,
    arm: str,
    split: str,
    seed: int,
    run: int | None = None,
) -> str:
    """Build a parseable run id. ``leave-repo`` becomes ``leaverepo``."""
    if exp < 1 or exp > 99:
        raise RunIdError(f"exp must be 1..99, got {exp}")
    if seed < 0:
        raise RunIdError(f"seed must be >= 0, got {seed}")
    parts = [
        f"exp-{exp:02d}",
        f"arm-{_entity(arm, field='arm')}",
        f"split-{_entity(split, field='split')}",
        f"seed-{seed}",
    ]
    if run is not None:
        if run < 2:
            raise RunIdError("run suffix is for reruns; use run>=2")
        parts.append(f"run-{run}")
    return "_".join(parts)


def parse_run_id(run_id: str) -> dict[str, str]:
    raw = (run_id or "").strip()
    if not raw or "/" in raw or raw in {".", ".."}:
        raise RunIdError(f"refusing run_id {run_id!r}")
    out: dict[str, str] = {}
    for part in raw.split("_"):
        match = _PAIR.fullmatch(part)
        if match is None:
            raise RunIdError(
                f"cannot parse {run_id!r}; expected key-value pairs like exp-02_arm-k1"
            )
        key, value = match.group(1), match.group(2)
        if key in out:
            raise RunIdError(f"duplicate entity {key!r} in {run_id!r}")
        out[key] = value
    for required in ("exp", "arm", "split", "seed"):
        if required not in out:
            raise RunIdError(f"{run_id!r} missing {required}")
    return out
