from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


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
