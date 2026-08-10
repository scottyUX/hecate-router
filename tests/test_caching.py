"""Offline tests for the generation cache (S9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hecate.caching import (
    CachedGeneration,
    GenerationCache,
    cache_key,
    decoding_fingerprint,
)
from hecate.data import GenerationRecord


def _decoding(temperature: float = 0.0, max_tokens: int = 4096) -> dict:
    # K-3: use consistent float typing (always 0.0, never 0) across runs.
    return {"temperature": temperature, "max_tokens": max_tokens}


def _key(
    *,
    instance_id: str = "django__django-12345",
    model_slug: str = "qwen/qwen-2.5-7b-instruct",
    prompt_hash: str = "abc123deadbeef",
    prompt_version: str = "v1",
    decoding: dict | None = None,
) -> str:
    params = decoding if decoding is not None else _decoding()
    return cache_key(
        instance_id=instance_id,
        model_slug=model_slug,
        prompt_hash=prompt_hash,
        prompt_version=prompt_version,
        decoding_fingerprint=decoding_fingerprint(params),
    )


def _entry(
    *,
    text: str = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-x\n+y\n",
    model_slug: str = "qwen/qwen-2.5-7b-instruct",
    decoding: dict | None = None,
) -> CachedGeneration:
    params = decoding if decoding is not None else _decoding()
    return CachedGeneration(
        raw_response=text,
        prompt_tokens=128,
        completion_tokens=64,
        decoding_params=dict(params),
        model_slug=model_slug,
    )


# --- US1: hit / miss / success-only ---


def test_put_then_get_returns_entry_with_zero_provider_calls(tmp_path: Path):
    """SC-001 / FR-003: repeated identity is a hit; cache never calls a provider."""
    api_calls = 0

    def fake_complete() -> CachedGeneration:
        nonlocal api_calls
        api_calls += 1
        return _entry()

    cache = GenerationCache(cache_dir=tmp_path)
    key = _key()

    hit = cache.get(key)
    if hit is None:
        cache.put(key, fake_complete())
    assert api_calls == 1

    hit = cache.get(key)
    if hit is None:
        cache.put(key, fake_complete())

    assert api_calls == 1
    assert hit is not None
    assert hit.raw_response.startswith("--- a/foo.py")


def test_get_absent_key_is_miss(tmp_path: Path):
    cache = GenerationCache(cache_dir=tmp_path)
    assert cache.get(_key()) is None


def test_hit_fields_populate_generation_record(tmp_path: Path):
    """FR-005 / K-10: hit carries fields needed for GenerationRecord."""
    cache = GenerationCache(cache_dir=tmp_path)
    key = _key()
    entry = _entry()
    cache.put(key, entry)
    hit = cache.get(key)
    assert hit is not None

    record = GenerationRecord(
        instance_id="django__django-12345",
        repo="django/django",
        base_commit="abc",
        model_slug=hit.model_slug,
        tier="small",
        raw_response=hit.raw_response,
        prompt_tokens=hit.prompt_tokens,
        completion_tokens=hit.completion_tokens,
        decoding_params=dict(hit.decoding_params),
    )
    assert record.raw_response == entry.raw_response
    assert record.prompt_tokens == 128
    assert record.completion_tokens == 64
    assert record.decoding_params == _decoding()
    assert record.model_slug == entry.model_slug


def test_raw_response_round_trips_non_ascii_and_large(tmp_path: Path):
    large = "日本語🚀\n" + ("x" * 50_000)
    cache = GenerationCache(cache_dir=tmp_path)
    key = _key()
    cache.put(key, _entry(text=large))
    hit = cache.get(key)
    assert hit is not None
    assert hit.raw_response == large


def test_empty_raw_response_cannot_be_cached():
    """FR-011 / SC-006: failures (empty/whitespace) cannot become hits."""
    with pytest.raises(ValueError, match="raw_response"):
        CachedGeneration(
            raw_response="",
            prompt_tokens=1,
            completion_tokens=1,
            decoding_params={},
            model_slug="m",
        )
    with pytest.raises(ValueError, match="raw_response"):
        CachedGeneration(
            raw_response="   \n\t",
            prompt_tokens=1,
            completion_tokens=1,
            decoding_params={},
            model_slug="m",
        )


# --- US2: restart / atomic / corrupt ---


def test_survives_new_cache_instance(tmp_path: Path):
    key = _key()
    GenerationCache(cache_dir=tmp_path).put(key, _entry())
    hit = GenerationCache(cache_dir=tmp_path).get(key)
    assert hit is not None
    assert hit.raw_response.startswith("--- a/foo.py")


def test_corrupt_and_schema_invalid_are_misses(tmp_path: Path):
    key = _key()
    cache = GenerationCache(cache_dir=tmp_path)
    path = tmp_path / f"{key}.json"
    path.write_text("{not json", encoding="utf-8")
    assert cache.get(key) is None

    path.write_text(json.dumps({"model_slug": "m"}), encoding="utf-8")
    assert cache.get(key) is None


def test_schema_version_mismatch_is_miss(tmp_path: Path):
    """Future format bump: missing/≠ CACHE_SCHEMA_VERSION → miss (K-12)."""
    key = _key()
    cache = GenerationCache(cache_dir=tmp_path)
    path = tmp_path / f"{key}.json"

    valid = _entry().to_dict()
    assert valid["schema_version"] == 1

    mismatched = dict(valid)
    mismatched["schema_version"] = 99
    path.write_text(json.dumps(mismatched), encoding="utf-8")
    assert cache.get(key) is None

    missing = dict(valid)
    del missing["schema_version"]
    path.write_text(json.dumps(missing), encoding="utf-8")
    assert cache.get(key) is None

    path.write_text(json.dumps(valid), encoding="utf-8")
    assert cache.get(key) is not None


def test_orphan_tmp_file_is_not_a_hit(tmp_path: Path):
    key = _key()
    cache = GenerationCache(cache_dir=tmp_path)
    (tmp_path / f"{key}.json.tmp-99999").write_text(
        _entry().to_json(), encoding="utf-8"
    )
    assert cache.get(key) is None


# --- US3: five-dimension key discrimination ---


def test_differ_only_instance_id_is_miss(tmp_path: Path):
    cache = GenerationCache(cache_dir=tmp_path)
    cache.put(_key(instance_id="a"), _entry())
    assert cache.get(_key(instance_id="b")) is None


def test_differ_only_model_slug_is_miss(tmp_path: Path):
    cache = GenerationCache(cache_dir=tmp_path)
    cache.put(_key(model_slug="model-a"), _entry(model_slug="model-a"))
    assert cache.get(_key(model_slug="model-b")) is None


def test_differ_only_prompt_hash_is_miss(tmp_path: Path):
    cache = GenerationCache(cache_dir=tmp_path)
    cache.put(_key(prompt_hash="hash-a"), _entry())
    assert cache.get(_key(prompt_hash="hash-b")) is None


def test_differ_only_prompt_version_is_miss(tmp_path: Path):
    """Byte-identical prompt under a bumped template version must miss."""
    cache = GenerationCache(cache_dir=tmp_path)
    cache.put(_key(prompt_version="v1"), _entry())
    assert cache.get(_key(prompt_version="v2")) is None


def test_differ_only_decoding_fingerprint_is_miss(tmp_path: Path):
    cache = GenerationCache(cache_dir=tmp_path)
    cache.put(_key(decoding=_decoding(0.0)), _entry(decoding=_decoding(0.0)))
    assert cache.get(_key(decoding=_decoding(0.7))) is None


def test_cache_key_is_deterministic():
    a = _key()
    b = _key()
    assert a == b
    assert len(a) == 64


def test_decoding_fingerprint_order_independent_and_value_sensitive():
    first = {"max_tokens": 4096, "temperature": 0.0}
    second = {"temperature": 0.0, "max_tokens": 4096}
    assert decoding_fingerprint(first) == decoding_fingerprint(second)
    assert decoding_fingerprint(_decoding(0.0)) != decoding_fingerprint(_decoding(0.7))


def test_cache_key_array_serialization_avoids_concat_collision():
    """K-1 regression: ('ab','c') must not collide with ('a','bc')."""
    left = cache_key("ab", "c", "p", "v1", "d")
    right = cache_key("a", "bc", "p", "v1", "d")
    assert left != right


# --- US4: read bypass ---


def test_read_bypass_misses_but_put_still_writes(tmp_path: Path):
    key = _key()
    GenerationCache(cache_dir=tmp_path).put(key, _entry())

    bypass = GenerationCache(cache_dir=tmp_path, read_bypass=True)
    assert bypass.get(key) is None
    bypass.put(key, _entry(text="fresh-success\n"))

    normal = GenerationCache(cache_dir=tmp_path)
    hit = normal.get(key)
    assert hit is not None
    assert hit.raw_response == "fresh-success\n"
