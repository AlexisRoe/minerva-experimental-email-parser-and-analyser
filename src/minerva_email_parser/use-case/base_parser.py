from __future__ import annotations

from typing import BinaryIO

# --- Use-case metadata (read by the CLI to build the selection menu) ---
NAME = "base-parser"
DESCRIPTION = "Stub use-case: parse a raw .eml byte stream (fill in the logic)."


def run(stream: BinaryIO) -> None:
    """Execute this use-case against a raw email byte stream.

    Args:
        stream: A binary stream of the loaded `.eml` file's contents.
    """
    raw = stream.read()
    print(f"[{NAME}] received {len(raw)} bytes — parsing not implemented yet")
