from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, BinaryIO, Protocol


class UseCaseError(Exception):
    """Raised when a use-case module cannot be loaded or is malformed."""


class UseCaseModule(Protocol):
    NAME: str
    DESCRIPTION: str

    def run(self, stream: BinaryIO) -> Any: ...


@dataclass(frozen=True)
class UseCase:
    """A discovered use-case: its metadata plus a way to run it."""

    name: str
    description: str
    path: Path
    module: ModuleType

    def run(self, stream: BinaryIO) -> Any:
        """Execute the use-case against a byte stream.

        Args:
            stream: A binary stream of the loaded email file's contents.

        Returns:
            A JSON-serializable result produced by the use-case.
        """
        return self.module.run(stream)


def discover_use_cases(use_case_dir: Path) -> list[UseCase]:
    """Discover all use-case modules in a directory.

    Each use-case is a `.py` file exposing module-level `NAME` and
    `DESCRIPTION` metadata plus a `run(stream)` function.

    Args:
        use_case_dir: Directory containing one `.py` file per use-case.

    Returns:
        The discovered use-cases, sorted by name.

    Raises:
        UseCaseError: If a `.py` file is missing required metadata or a `run` function.
    """
    use_cases: list[UseCase] = []

    # Sorted once at the end (by `name`, which may differ from the file
    # name) — no need to also sort the glob results here.
    for path in use_case_dir.glob("*.py"):
        if path.stem.startswith("_"):
            continue

        module = _load_module(path)
        name = getattr(module, "NAME", None)
        description = getattr(module, "DESCRIPTION", None)
        run = getattr(module, "run", None)
        if not name or not description or not callable(run):
            raise UseCaseError(f"{path} must define NAME, DESCRIPTION, and a run(stream) function")

        use_cases.append(UseCase(name=name, description=description, path=path, module=module))

    return sorted(use_cases, key=lambda uc: uc.name)


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise UseCaseError(f"Could not load use-case module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module
