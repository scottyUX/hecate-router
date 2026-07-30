"""Extract one unified diff from a raw model response (S8).

Pure, offline, deterministic. ``unidiff`` validates structure only; the emitted
patch is always a byte-exact substring of the input (wrappers/prose removed).
"""

from __future__ import annotations

from dataclasses import dataclass

from unidiff import PatchSet
from unidiff.errors import UnidiffParseError

# Failure reasons (in-memory diagnostic only — not a GenerationRecord field).
REASON_EMPTY = "empty"
REASON_NO_DIFF = "no_diff_found"
REASON_INVALID = "invalid_structure"
REASON_AMBIGUOUS = "ambiguous"

_DIFF_START_PREFIXES = ("diff --git ", "--- ", "Index: ")
_DIFF_HEADER_PREFIXES = (
    "diff --git ",
    "index ",
    "--- ",
    "+++ ",
    "old mode ",
    "new mode ",
    "deleted file mode ",
    "new file mode ",
    "similarity index ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "Index: ",
)
_NO_NEWLINE_MARKER = r"\ No newline at end of file"


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome of ``extract_patch`` — maps onto GenerationRecord patch fields."""

    raw_response: str
    patch_parse_ok: bool
    extracted_patch: str | None
    reason: str | None = None


def extract_patch(raw_response: str) -> ExtractionResult:
    """Convert one raw model response into a normalized patch or a parse failure.

    Never raises for malformed input. Always preserves ``raw_response`` byte-for-byte.
    """
    if raw_response is None:  # type: ignore[unreachable]
        raw_response = ""

    if not raw_response.strip():
        return ExtractionResult(
            raw_response=raw_response,
            patch_parse_ok=False,
            extracted_patch=None,
            reason=REASON_EMPTY,
        )

    fenced = _find_fenced_regions(raw_response)
    validating_fenced: list[str] = []
    invalid_looking_fenced: list[str] = []
    for interior in fenced:
        if _is_structurally_valid(interior):
            validating_fenced.append(interior)
        elif _looks_like_diff_region(interior):
            invalid_looking_fenced.append(interior)

    if len(validating_fenced) > 1:
        return _fail(raw_response, REASON_AMBIGUOUS)
    if len(validating_fenced) == 1:
        return _ok(raw_response, validating_fenced[0])

    # No validating fenced candidate — try unfenced (research D2).
    unfenced = _find_unfenced_regions(raw_response)
    validating_unfenced: list[str] = []
    invalid_unfenced: list[str] = []
    for region in unfenced:
        if _is_structurally_valid(region):
            validating_unfenced.append(region)
        else:
            invalid_unfenced.append(region)

    if len(validating_unfenced) > 1:
        return _fail(raw_response, REASON_AMBIGUOUS)
    if len(validating_unfenced) == 1:
        return _ok(raw_response, validating_unfenced[0])

    if invalid_looking_fenced or invalid_unfenced:
        return _fail(raw_response, REASON_INVALID)

    return _fail(raw_response, REASON_NO_DIFF)


def _ok(raw: str, patch: str) -> ExtractionResult:
    return ExtractionResult(
        raw_response=raw,
        patch_parse_ok=True,
        extracted_patch=patch,
        reason=None,
    )


def _fail(raw: str, reason: str) -> ExtractionResult:
    return ExtractionResult(
        raw_response=raw,
        patch_parse_ok=False,
        extracted_patch=None,
        reason=reason,
    )


def _is_hunk_body_line(line: str) -> bool:
    """True if line is hunk body (space/+/−) or the no-newline marker."""
    body = line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line
    if body == _NO_NEWLINE_MARKER or body.startswith(_NO_NEWLINE_MARKER):
        return True
    return bool(body) and body[0] in (" ", "+", "-")


def _is_fence_delimiter_line(line: str) -> tuple[str, str] | None:
    """Return (marker, info) if this line opens/closes a fence; else None.

    Fence delimiters are recognized only on lines that are NOT hunk-body lines.
    """
    if _is_hunk_body_line(line):
        return None
    body = line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line
    stripped = body.lstrip()
    for marker in ("```", "~~~"):
        if stripped.startswith(marker):
            rest = stripped[len(marker) :]
            # Closing fence: marker only (optional trailing spaces). Opening: optional info.
            return marker, rest.strip()
    return None


def _find_fenced_regions(text: str) -> list[str]:
    """Return interiors of complete Markdown fences (``` or ~~~)."""
    lines = _split_preserving_newlines(text)
    interiors: list[str] = []
    i = 0
    while i < len(lines):
        delim = _is_fence_delimiter_line(lines[i])
        if delim is None:
            i += 1
            continue
        marker, _info = delim
        # Look for matching close.
        j = i + 1
        while j < len(lines):
            close = _is_fence_delimiter_line(lines[j])
            if close is not None and close[0] == marker:
                interiors.append("".join(lines[i + 1 : j]))
                i = j + 1
                break
            j += 1
        else:
            # Unmatched opening fence — skip this line (no candidate).
            i += 1
    return interiors


def _is_diff_start_line(line: str) -> bool:
    body = line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line
    return any(body.startswith(p) for p in _DIFF_START_PREFIXES)


def _is_diff_line(line: str) -> bool:
    """Whether a line continues an unfenced diff region (contract §4.2)."""
    body = line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line
    if body == "":
        # Truly empty (zero-width) line — region boundary, not a diff line.
        return False
    if body == _NO_NEWLINE_MARKER or body.startswith(_NO_NEWLINE_MARKER):
        return True
    if body[0] in (" ", "+", "-"):
        return True
    if any(body.startswith(p) for p in _DIFF_HEADER_PREFIXES):
        return True
    if body.startswith("@@ ") and " @@" in body[3:]:
        return True
    # Bare @@ hunk headers sometimes appear without trailing section text.
    if body.startswith("@@") and "@@" in body[2:]:
        return True
    return False


def _find_unfenced_regions(text: str) -> list[str]:
    lines = _split_preserving_newlines(text)
    regions: list[str] = []
    i = 0
    while i < len(lines):
        if not _is_diff_start_line(lines[i]):
            i += 1
            continue
        start = i
        i += 1
        while i < len(lines) and _is_diff_line(lines[i]):
            i += 1
        regions.append("".join(lines[start:i]))
        # i is already at the first non-diff line (or EOF); continue from there.
    return regions


def _looks_like_diff_region(text: str) -> bool:
    if not text.strip():
        return False
    for line in _split_preserving_newlines(text):
        if _is_diff_start_line(line) or _is_diff_line(line):
            return True
    return False


def _is_structurally_valid(candidate: str) -> bool:
    """True iff unidiff parses ≥1 file with ≥1 complete hunk (validator only)."""
    if not candidate.strip():
        return False
    # Coerce newlines for the validator copy only; emit path uses original bytes.
    normalized = candidate.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized_for_parse = normalized + "\n"
    else:
        normalized_for_parse = normalized
    try:
        patch_set = PatchSet(normalized_for_parse)
    except (UnidiffParseError, ValueError, TypeError):
        return False
    if len(patch_set) < 1:
        return False
    for patched_file in patch_set:
        if len(patched_file) < 1:
            return False
    return True


def _split_preserving_newlines(text: str) -> list[str]:
    """Split into lines keeping each line's terminator (\\n or \\r\\n)."""
    if not text:
        return []
    lines: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        j = i
        while j < n and text[j] != "\n":
            j += 1
        if j < n:
            # Include \\n; if preceded by \\r, keep CRLF as the terminator.
            lines.append(text[i : j + 1])
            i = j + 1
        else:
            lines.append(text[i:j])
            break
    return lines
