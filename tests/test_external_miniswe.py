"""Tests for externally sourced mini-SWE-agent label joins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hecate.data.external_miniswe import (
    CSV_NAME,
    EXPECTED_N,
    FIELDNAMES,
    JSON_NAME,
    LARGE_PUBLISHED_PCT,
    LARGE_RESOLVED_COUNT,
    OPUS_GIT_PEEK_IDS,
    OPUS_GIT_PEEK_RESOLVED_IDS,
    OPUS_GIT_PEEK_SENSITIVITY_PCT,
    SMALL_PUBLISHED_PCT,
    SMALL_RESOLVED_COUNT,
    JoinError,
    git_peek_sensitivity,
    join_labels,
    parse_repo,
    percent_one_decimal,
    read_joined_csv,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTERNAL_DIR = _REPO_ROOT / "data" / "external"
_CSV_PATH = _EXTERNAL_DIR / CSV_NAME
_JSON_PATH = _EXTERNAL_DIR / JSON_NAME


def _details(resolved_by_id: dict[str, bool]) -> dict[str, dict[str, bool]]:
    return {iid: {"resolved": ok} for iid, ok in resolved_by_id.items()}


def test_parse_repo_owner_name_issue():
    assert parse_repo("django__django-12050") == "django/django"
    assert parse_repo("pytest-dev__pytest-6197") == "pytest-dev/pytest"
    assert parse_repo("scikit-learn__scikit-learn-14087") == "scikit-learn/scikit-learn"


def test_parse_repo_rejects_malformed_ids():
    with pytest.raises(JoinError):
        parse_repo("django-12050")
    with pytest.raises(JoinError):
        parse_repo("django__django")


def test_join_labels_inner_join_sorted():
    small = _details(
        {
            "django__django-2": False,
            "pytest-dev__pytest-1": True,
            "astropy__astropy-3": False,
        }
    )
    large = _details(
        {
            "pytest-dev__pytest-1": True,
            "django__django-2": True,
            "astropy__astropy-3": False,
        }
    )
    rows = join_labels(
        small,
        large,
        expected_n=3,
        small_published_pct=33.3,
        large_published_pct=66.7,
    )
    assert [row.instance_id for row in rows] == [
        "astropy__astropy-3",
        "django__django-2",
        "pytest-dev__pytest-1",
    ]
    assert rows[2].repo == "pytest-dev/pytest"
    assert rows[2].small_model_resolved is True
    assert rows[1].large_model_resolved is True


def test_join_labels_fails_on_size_mismatch():
    small = _details({"django__django-1": True})
    large = _details({"django__django-1": True, "django__django-2": False})
    with pytest.raises(JoinError, match="expected 2"):
        join_labels(
            small,
            large,
            expected_n=2,
            small_published_pct=100.0,
            large_published_pct=50.0,
        )


def test_join_labels_fails_on_missing_ids():
    small = _details({"django__django-1": True, "django__django-2": False})
    large = _details({"django__django-1": True, "astropy__astropy-3": False})
    with pytest.raises(JoinError, match="instance_id sets do not match"):
        join_labels(
            small,
            large,
            expected_n=2,
            small_published_pct=50.0,
            large_published_pct=50.0,
        )


def test_join_labels_fails_on_rate_mismatch():
    small = _details({"django__django-1": True, "django__django-2": False})
    large = _details({"django__django-1": True, "django__django-2": False})
    with pytest.raises(JoinError, match="does not match published"):
        join_labels(
            small,
            large,
            expected_n=2,
            small_published_pct=55.4,
            large_published_pct=67.6,
        )


def test_committed_csv_and_json_match_published_rates():
    assert _CSV_PATH.is_file(), f"missing committed labels: {_CSV_PATH}"
    assert _JSON_PATH.is_file(), f"missing committed labels: {_JSON_PATH}"
    csv_rows = read_joined_csv(_CSV_PATH)
    json_rows = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    assert len(csv_rows) == EXPECTED_N
    assert len(json_rows) == EXPECTED_N
    assert list(csv_rows[0].to_dict()) == list(FIELDNAMES)
    csv_ids = [row.instance_id for row in csv_rows]
    json_ids = [row["instance_id"] for row in json_rows]
    assert csv_ids == sorted(csv_ids)
    assert csv_ids == json_ids
    assert len(set(csv_ids)) == EXPECTED_N
    small_resolved = sum(1 for row in csv_rows if row.small_model_resolved)
    large_resolved = sum(1 for row in csv_rows if row.large_model_resolved)
    assert small_resolved == SMALL_RESOLVED_COUNT
    assert large_resolved == LARGE_RESOLVED_COUNT
    assert percent_one_decimal(small_resolved, EXPECTED_N) == SMALL_PUBLISHED_PCT
    assert percent_one_decimal(large_resolved, EXPECTED_N) == LARGE_PUBLISHED_PCT
    for csv_row, json_row in zip(csv_rows, json_rows, strict=True):
        assert csv_row.to_dict() == json_row


def test_committed_opus_git_peek_sensitivity():
    rows = read_joined_csv(_CSV_PATH)
    peek = git_peek_sensitivity(rows)
    assert peek["n_flagged"] == len(OPUS_GIT_PEEK_IDS)
    assert peek["flagged_resolved_instance_ids"] == list(OPUS_GIT_PEEK_RESOLVED_IDS)
    assert peek["sensitivity_recode_false_pct"] == OPUS_GIT_PEEK_SENSITIVITY_PCT
    assert peek["qwen_git_peek_count"] == 0
    assert peek["keep_all_rows"] is True
