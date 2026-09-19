from __future__ import annotations

import io
from pathlib import Path

import pytest

from minerva_email_parser.use_case_loader import UseCaseError, discover_use_cases


def _bytes_io(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


VALID_USE_CASE = """\
from __future__ import annotations

from typing import Any, BinaryIO

NAME = "counts-bytes"
DESCRIPTION = "Counts the bytes in the stream."


def run(stream: BinaryIO) -> dict[str, Any]:
    return {"byteCount": len(stream.read())}
"""

INVALID_USE_CASE = """\
NAME = "missing-run"
DESCRIPTION = "No run() defined."
"""


def test_discover_use_cases_loads_metadata_and_run(tmp_path: Path) -> None:
    (tmp_path / "counts_bytes.py").write_text(VALID_USE_CASE)

    use_cases = discover_use_cases(tmp_path)

    assert len(use_cases) == 1
    assert use_cases[0].name == "counts-bytes"
    assert use_cases[0].description == "Counts the bytes in the stream."
    assert use_cases[0].run(_bytes_io(b"abc")) == {"byteCount": 3}


def test_discover_use_cases_skips_underscore_prefixed_files(tmp_path: Path) -> None:
    (tmp_path / "_helpers.py").write_text("NAME = 'x'")

    assert discover_use_cases(tmp_path) == []


def test_discover_use_cases_raises_on_missing_metadata(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text(INVALID_USE_CASE)

    with pytest.raises(UseCaseError):
        discover_use_cases(tmp_path)
