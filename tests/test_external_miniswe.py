"""Tests for externally sourced mini-SWE-agent label joins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hecate.data.external_miniswe import (
    BOTH_RESOLVED_COUNT,
    CSV_NAME,
    EXPECTED_N,
    FIELDNAMES,
    HEADROOM_PP,
    JSON_NAME,
    LARGE_ONLY_COUNT,
    LARGE_PUBLISHED_PCT,
    LARGE_RESOLVED_COUNT,
    NEITHER_COUNT,
    OPUS_GIT_PEEK_IDS,
    OPUS_GIT_PEEK_RESOLVED_IDS,
    OPUS_GIT_PEEK_SENSITIVITY_PCT,
    ORACLE_PCT,
    ORACLE_RESOLVED_COUNT,
    SMALL_ONLY_COUNT,
    SMALL_PUBLISHED_PCT,
    SMALL_RESOLVED_COUNT,
    TEXT_CSV_NAME,
    TEXT_FIELDNAMES,
    TEXT_JSON_NAME,
    JoinError,
    JoinedLabel,
    complementarity,
    git_peek_sensitivity,
    join_and_write_text,
    join_labels,
    join_problem_statements,
    parse_repo,
    percent_one_decimal,
    read_joined_csv,
    read_joined_text_csv,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTERNAL_DIR = _REPO_ROOT / "data" / "external"
_CSV_PATH = _EXTERNAL_DIR / CSV_NAME
_JSON_PATH = _EXTERNAL_DIR / JSON_NAME
_TEXT_CSV_PATH = _EXTERNAL_DIR / TEXT_CSV_NAME
_TEXT_JSON_PATH = _EXTERNAL_DIR / TEXT_JSON_NAME


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


def _label(
    instance_id: str, *, small: bool, large: bool, repo: str | None = None
) -> JoinedLabel:
    return JoinedLabel(
        instance_id=instance_id,
        repo=repo if repo is not None else parse_repo(instance_id),
        small_model_resolved=small,
        large_model_resolved=large,
    )


def _verified(
    instance_id: str,
    *,
    statement: str = "issue body",
    commit: str = "abc123",
    repo: str | None = None,
) -> dict[str, str]:
    payload = {
        "problem_statement": statement,
        "base_commit": commit,
    }
    if repo is not None:
        payload["repo"] = repo
    return payload


def test_join_problem_statements_happy_path_ignores_extra_ids():
    labels = [
        _label("astropy__astropy-3", small=False, large=False),
        _label("django__django-2", small=False, large=True),
        _label("pytest-dev__pytest-1", small=True, large=True),
    ]
    by_id = {
        "astropy__astropy-3": _verified("astropy__astropy-3", repo="astropy/astropy"),
        "django__django-2": _verified(
            "django__django-2", statement="django bug", repo="django/django"
        ),
        "pytest-dev__pytest-1": _verified(
            "pytest-dev__pytest-1", commit="def456", repo="pytest-dev/pytest"
        ),
        "extra__extra-9": _verified("extra__extra-9", repo="extra/extra"),
    }
    rows = join_problem_statements(labels, by_id)
    assert [row.instance_id for row in rows] == [lab.instance_id for lab in labels]
    assert rows[1].problem_statement == "django bug"
    assert rows[2].base_commit == "def456"
    assert "patch" not in rows[0].to_dict()
    assert "test_patch" not in rows[0].to_dict()


def test_join_problem_statements_fails_on_missing_id():
    labels = [
        _label("django__django-1", small=True, large=True),
        _label("django__django-2", small=False, large=False),
    ]
    by_id = {"django__django-1": _verified("django__django-1", repo="django/django")}
    with pytest.raises(JoinError, match="missing from SWE-bench Verified"):
        join_problem_statements(labels, by_id)


def test_join_problem_statements_fails_on_empty_problem_statement():
    labels = [_label("django__django-1", small=True, large=True)]
    by_id = {
        "django__django-1": _verified(
            "django__django-1", statement="  \n", repo="django/django"
        )
    }
    with pytest.raises(JoinError, match="empty problem_statement"):
        join_problem_statements(labels, by_id)


def test_join_problem_statements_fails_on_repo_mismatch():
    labels = [_label("django__django-1", small=True, large=True)]
    by_id = {
        "django__django-1": _verified("django__django-1", repo="flask/flask"),
    }
    with pytest.raises(JoinError, match="repo mismatch"):
        join_problem_statements(labels, by_id)


def test_join_and_write_text_does_not_write_on_join_error(tmp_path: Path):
    labels = [_label("django__django-1", small=True, large=True)]
    with pytest.raises(JoinError, match="missing from SWE-bench Verified"):
        join_and_write_text(labels, {}, tmp_path)
    assert not (tmp_path / TEXT_CSV_NAME).exists()
    assert not (tmp_path / TEXT_JSON_NAME).exists()


def test_text_csv_json_roundtrip_multiline(tmp_path: Path):
    labels = [_label("django__django-1", small=True, large=False)]
    body = "line one\nline two\nquoted \"text\""
    by_id = {
        "django__django-1": _verified(
            "django__django-1", statement=body, commit="deadbeef", repo="django/django"
        )
    }
    rows, csv_path, json_path = join_and_write_text(labels, by_id, tmp_path)
    assert csv_path.is_file()
    restored = read_joined_text_csv(csv_path)
    assert restored == rows
    assert restored[0].problem_statement == body
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_rows[0]["problem_statement"] == body
    assert list(json_rows[0]) == list(TEXT_FIELDNAMES)


def test_committed_labels_complementarity():
    rows = read_joined_csv(_CSV_PATH)
    stats = complementarity(rows)
    assert stats["both_resolved"] == BOTH_RESOLVED_COUNT
    assert stats["small_only"] == SMALL_ONLY_COUNT
    assert stats["large_only"] == LARGE_ONLY_COUNT
    assert stats["neither"] == NEITHER_COUNT
    assert stats["oracle_resolved"] == ORACLE_RESOLVED_COUNT
    assert stats["oracle_pct"] == ORACLE_PCT
    assert stats["always_small_pct"] == SMALL_PUBLISHED_PCT
    assert stats["always_large_pct"] == LARGE_PUBLISHED_PCT
    assert stats["headroom_pp"] == HEADROOM_PP


def test_committed_with_text_matches_labels():
    assert _TEXT_CSV_PATH.is_file(), f"missing joined text CSV: {_TEXT_CSV_PATH}"
    assert _TEXT_JSON_PATH.is_file(), f"missing joined text JSON: {_TEXT_JSON_PATH}"
    labels = read_joined_csv(_CSV_PATH)
    text_rows = read_joined_text_csv(_TEXT_CSV_PATH)
    json_rows = json.loads(_TEXT_JSON_PATH.read_text(encoding="utf-8"))
    assert len(text_rows) == EXPECTED_N
    assert len(json_rows) == EXPECTED_N
    assert [row.instance_id for row in text_rows] == [row.instance_id for row in labels]
    assert all(row.problem_statement.strip() for row in text_rows)
    assert all(row.base_commit.strip() for row in text_rows)
    small_resolved = sum(1 for row in text_rows if row.small_model_resolved)
    large_resolved = sum(1 for row in text_rows if row.large_model_resolved)
    assert small_resolved == SMALL_RESOLVED_COUNT
    assert large_resolved == LARGE_RESOLVED_COUNT
    for label, text_row, json_row in zip(labels, text_rows, json_rows, strict=True):
        assert text_row.instance_id == label.instance_id
        assert text_row.repo == label.repo
        assert text_row.small_model_resolved == label.small_model_resolved
        assert text_row.large_model_resolved == label.large_model_resolved
        assert json_row["instance_id"] == text_row.instance_id
        assert json_row["problem_statement"] == text_row.problem_statement
        assert "patch" not in json_row
        assert "test_patch" not in json_row

