from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO


def discover_assets(assets_dir: Path, pattern: str = "*.eml") -> list[Path]:
    """List available asset files, sorted by name.

    Args:
        assets_dir: Directory containing asset files.
        pattern: Glob pattern used to filter files.

    Returns:
        Matching file paths, sorted by name.
    """
    return sorted(assets_dir.glob(pattern))


@contextmanager
def open_asset_stream(path: Path) -> Iterator[BinaryIO]:
    """Open a local file and yield it as a binary stream.

    Args:
        path: Path to the file on disk (e.g. an `.eml` asset).

    Yields:
        The open binary file object.
    """
    with path.open("rb") as stream:
        yield stream


def write_json_output(output_dir: Path, file_name: str, result: Any) -> Path:
    """Write a use-case result to a JSON file in the output directory.

    Args:
        output_dir: Directory the file is written into (created if missing).
        file_name: Name of the file to write, e.g. `base-parser_base.eml.json`.
        result: A JSON-serializable value to write.

    Returns:
        The path the result was written to.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name
    output_path.write_text(json.dumps(result, indent=2))

    return output_path
