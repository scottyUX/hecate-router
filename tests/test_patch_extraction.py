"""Offline fixture suite for S8 patch extraction (zero network / spend)."""

from __future__ import annotations

import pytest

from hecate.generation import ExtractionResult, extract_patch
from hecate.generation.patch import (
    REASON_AMBIGUOUS,
    REASON_EMPTY,
    REASON_INVALID,
    REASON_NO_DIFF,
)

# --- Success fixtures -------------------------------------------------------

PLAIN_SINGLE = """\
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-x = 1
+x = 2
"""

FENCED_WITH_PROSE = """\
Here's the fix:

```diff
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-x = 1
+x = 2
```

Hope that helps!
"""

FENCED_BARE = """\
```
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-x = 1
+x = 2
```
"""

MULTI_FILE = """\
--- a/a.py
+++ b/a.py
@@ -1 +1 @@
-old_a
+new_a
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
-old_b
+new_b
"""

ADD_FILE = """\
diff --git a/new.py b/new.py
new file mode 100644
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+hello
+world
"""

DELETE_FILE = """\
diff --git a/gone.py b/gone.py
deleted file mode 100644
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-bye
-now
"""

RENAME_FILE = """\
diff --git a/old.py b/new.py
similarity index 100%
rename from old.py
rename to new.py
"""

# Rename-only with no hunks may fail unidiff (≥1 hunk required). Use rename + mod:
RENAME_WITH_HUNK = """\
diff --git a/old.py b/new.py
similarity index 80%
rename from old.py
rename to new.py
--- a/old.py
+++ b/new.py
@@ -1 +1 @@
-alpha
+beta
"""

NON_ASCII = """\
--- a/café.py
+++ b/café.py
@@ -1 +1 @@
-naïve
+niçoise
"""

CRLF_PATCH = (
    "--- a/app.py\r\n"
    "+++ b/app.py\r\n"
    "@@ -1 +1 @@\r\n"
    "-x\r\n"
    "+y\r\n"
)

NO_FINAL_NEWLINE = (
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1 +1 @@\n"
    "-x\n"
    "+y"
)

BLANK_CONTEXT_LINE = """\
--- a/app.py
+++ b/app.py
@@ -1,3 +1,3 @@
 line1
 
-line3
+line3_new
"""

FENCE_INSIDE_HUNK = """\
```diff
--- a/README.md
+++ b/README.md
@@ -1,2 +1,5 @@
 # Title
+```
+code
+```
 text
```
"""


def test_plain_single_file_success() -> None:
    result = extract_patch(PLAIN_SINGLE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == PLAIN_SINGLE
    assert result.reason is None
    assert result.raw_response == PLAIN_SINGLE


def test_fenced_with_prose_strips_wrapper() -> None:
    result = extract_patch(FENCED_WITH_PROSE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == PLAIN_SINGLE
    assert result.raw_response == FENCED_WITH_PROSE


def test_fenced_bare_info_string() -> None:
    result = extract_patch(FENCED_BARE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == PLAIN_SINGLE


def test_multi_file_order_preserved() -> None:
    result = extract_patch(MULTI_FILE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == MULTI_FILE
    assert result.extracted_patch.index("a.py") < result.extracted_patch.index("b.py")


def test_add_delete_rename_modification() -> None:
    for fixture in (ADD_FILE, DELETE_FILE, RENAME_WITH_HUNK, PLAIN_SINGLE):
        result = extract_patch(fixture)
        assert result.patch_parse_ok is True, fixture[:40]
        assert result.extracted_patch == fixture


def test_non_ascii_preserved() -> None:
    result = extract_patch(NON_ASCII)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == NON_ASCII
    assert "café" in result.extracted_patch
    assert "niçoise" in result.extracted_patch


def test_crlf_preserved_exactly() -> None:
    result = extract_patch(CRLF_PATCH)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == CRLF_PATCH
    assert "\r\n" in result.extracted_patch


def test_missing_final_newline_preserved() -> None:
    result = extract_patch(NO_FINAL_NEWLINE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == NO_FINAL_NEWLINE
    assert not result.extracted_patch.endswith("\n")


def test_blank_context_line_keeps_one_region() -> None:
    result = extract_patch(BLANK_CONTEXT_LINE)
    assert result.patch_parse_ok is True
    assert result.extracted_patch == BLANK_CONTEXT_LINE


def test_fence_marker_inside_hunk_not_second_region() -> None:
    result = extract_patch(FENCE_INSIDE_HUNK)
    assert result.patch_parse_ok is True
    assert result.extracted_patch is not None
    assert "```" in result.extracted_patch


# --- Failure fixtures -------------------------------------------------------


def test_empty_and_whitespace() -> None:
    for raw in ("", "   \n\t  \n"):
        result = extract_patch(raw)
        assert result.patch_parse_ok is False
        assert result.extracted_patch is None
        assert result.reason == REASON_EMPTY
        assert result.raw_response == raw


def test_prose_only() -> None:
    raw = "Sorry, I couldn't produce a patch."
    result = extract_patch(raw)
    assert result.patch_parse_ok is False
    assert result.extracted_patch is None
    assert result.reason == REASON_NO_DIFF
    assert result.raw_response == raw


def test_malformed_header() -> None:
    raw = "--- not a real patch\nthis is broken\n"
    result = extract_patch(raw)
    assert result.patch_parse_ok is False
    assert result.extracted_patch is None
    assert result.reason in {REASON_INVALID, REASON_NO_DIFF}
    assert result.raw_response == raw


def test_truncated_hunk() -> None:
    raw = """\
--- a/app.py
+++ b/app.py
@@ -1,5 +1,5 @@
-line1
"""
    result = extract_patch(raw)
    assert result.patch_parse_ok is False
    assert result.extracted_patch is None
    assert result.reason == REASON_INVALID
    assert result.raw_response == raw


def test_two_fenced_diffs_ambiguous() -> None:
    raw = f"```diff\n{PLAIN_SINGLE}```\n\nand another:\n\n```diff\n{PLAIN_SINGLE}```\n"
    result = extract_patch(raw)
    assert result.patch_parse_ok is False
    assert result.extracted_patch is None
    assert result.reason == REASON_AMBIGUOUS
    assert result.raw_response == raw


def test_two_unfenced_regions_ambiguous() -> None:
    raw = PLAIN_SINGLE + "\nSome prose between.\n\n" + PLAIN_SINGLE
    result = extract_patch(raw)
    assert result.patch_parse_ok is False
    assert result.extracted_patch is None
    assert result.reason == REASON_AMBIGUOUS


def test_never_raises_on_garbage() -> None:
    for raw in ("", "???", "```\n```\n", "\x00\x01", "---\n+++"):
        result = extract_patch(raw)
        assert isinstance(result, ExtractionResult)
        assert result.raw_response == raw


def test_result_invariants() -> None:
    ok = extract_patch(PLAIN_SINGLE)
    assert ok.patch_parse_ok is True
    assert ok.extracted_patch is not None
    assert ok.reason is None

    bad = extract_patch("nope")
    assert bad.patch_parse_ok is False
    assert bad.extracted_patch is None
    assert bad.reason is not None


def test_frozen_result() -> None:
    result = extract_patch(PLAIN_SINGLE)
    with pytest.raises(Exception):
        result.patch_parse_ok = False  # type: ignore[misc]


def test_import_from_package_root() -> None:
    from hecate.generation import extract_patch as ep

    assert ep(PLAIN_SINGLE).patch_parse_ok is True
