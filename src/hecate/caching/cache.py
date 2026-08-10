"""Disk-backed generation cache keyed by full generation identity (S9).

Keys bind ``(instance_id, model_slug, prompt_hash, prompt_version,
decoding_fingerprint)`` so a hit is only served for a comparable generation.
Entries persist under the gitignored cache area and survive process restarts.
Only successful outcomes can be stored; the OpenRouter client stays cache-unaware.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CACHE_SCHEMA_VERSION = 1


def _repo_root() -> Path:
    # src/hecate/caching/cache.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def default_cache_dir() -> Path:
    """Default on-disk store: ``data/cache/generations/`` (gitignored)."""
    return _repo_root() / "data" / "cache" / "generations"


def decoding_fingerprint(decoding_params: dict[str, Any]) -> str:
    """Hex SHA-256 of canonical JSON for decoding params (order-independent).

    Callers MUST supply consistently-typed values across runs (e.g. always
    ``0.0``, never ``0``): differing numeric types serialize differently and
    would cause a false miss — never a false hit (contract K-3).
    """
    canonical = json.dumps(
        decoding_params,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_key(
    instance_id: str,
    model_slug: str,
    prompt_hash: str,
    prompt_version: str,
    decoding_fingerprint: str,
) -> str:
    """Hex SHA-256 over a JSON array of the five identity strings.

    Uses a JSON array (not concatenation) so ``("ab","c")`` and ``("a","bc")``
    cannot collide.
    """
    canonical = json.dumps(
        [
            instance_id,
            model_slug,
            prompt_hash,
            prompt_version,
            decoding_fingerprint,
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedGeneration:
    """A persisted successful provider outcome for one cache key."""

    raw_response: str
    prompt_tokens: int | None
    completion_tokens: int | None
    decoding_params: dict[str, Any]
    model_slug: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_response, str) or not self.raw_response.strip():
            raise ValueError(
                "raw_response must be a non-empty, non-whitespace string "
                "(failures cannot be cached)"
            )
        if not isinstance(self.model_slug, str) or not self.model_slug:
            raise ValueError("model_slug must be a non-empty string")
        if not isinstance(self.decoding_params, dict):
            raise ValueError("decoding_params must be a dict")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = CACHE_SCHEMA_VERSION
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedGeneration | None:
        """Reconstruct an entry, or ``None`` if the payload is schema-invalid.

        Missing or mismatched ``schema_version`` is a miss so a future format
        bump auto-invalidates old on-disk entries.
        """
        if not isinstance(data, dict):
            return None
        if data.get("schema_version") != CACHE_SCHEMA_VERSION:
            return None
        required = (
            "raw_response",
            "prompt_tokens",
            "completion_tokens",
            "decoding_params",
            "model_slug",
        )
        if any(field not in data for field in required):
            return None
        try:
            return cls(
                raw_response=data["raw_response"],
                prompt_tokens=data["prompt_tokens"],
                completion_tokens=data["completion_tokens"],
                decoding_params=data["decoding_params"],
                model_slug=data["model_slug"],
            )
        except (TypeError, ValueError):
            return None

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> CachedGeneration | None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        return cls.from_dict(data)


class GenerationCache:
    """Filesystem-backed store for successful generation outcomes."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        *,
        read_bypass: bool = False,
    ) -> None:
        self._cache_dir = (
            Path(cache_dir) if cache_dir is not None else default_cache_dir()
        )
        self._read_bypass = read_bypass

    def _path_for(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, key: str) -> CachedGeneration | None:
        if self._read_bypass:
            return None
        path = self._path_for(key)
        if not path.is_file():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        return CachedGeneration.from_json(text)

    def put(self, key: str, entry: CachedGeneration) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(key)
        # Temp file in the *same* directory so os.replace is atomic (same FS).
        tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
        try:
            tmp_path.write_text(entry.to_json(), encoding="utf-8")
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
